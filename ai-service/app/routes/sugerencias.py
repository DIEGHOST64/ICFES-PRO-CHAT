"""
RF-09, RF-23: Endpoint GET /sugerencias — Preguntas de práctica
Devuelve preguntas aleatorias filtradas por módulo (general o específico del programa).
Usa Gemini para generar preguntas estructuradas desde fragmentos del cuadernillo ICFES.
"""

import json
import random
import asyncio
import re
import threading
import time
from fastapi import APIRouter, Query as QueryParam, BackgroundTasks
from pydantic import BaseModel

from app.services.chroma_client import ChromaService
from app.services.rag_service import get_modulo
from app.services.gemini_client import (
    get_gemini_quiz_model,
    generate_fun_facts,
    generate_admin_analytics_report,
    generate_practice_support,
)

router = APIRouter()


class Pregunta(BaseModel):
    id: str
    texto_base: str = ""
    enunciado: str
    opciones: list[str]
    respuesta_correcta: str
    explicacion: str
    competencia: str
    programa: str
    tipo_ingles: str | None = None
    nivel_cefr: str | None = None
    nivel_dificultad: str | None = None
    bloque_id: str | None = None
    orden_en_bloque: int | None = None
    preguntas_en_bloque: int | None = None


GENERAL_COMPETENCIAS_BASE = [
    "Lectura Crítica",
    "Razonamiento Cuantitativo",
    "Comunicación Escrita",
    "Inglés",
    "Ciudadanas",
]


SUGERENCIAS_CACHE_TTL_SECONDS = 86400
SUGERENCIAS_CACHE_MAX_ITEMS = 512
_SUGERENCIAS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_SUGERENCIAS_CACHE_LOCK = threading.Lock()


NON_ACADEMIC_MARKERS = [
    "terminos y condiciones",
    "términos y condiciones",
    "derechos de autor",
    "todos los derechos reservados",
    "ninguna persona natural o juridica",
    "ninguna persona natural o jurídica",
    "prohibida su reproduccion",
    "prohibida su reproducción",
    "unicamente esta autorizado su uso",
    "únicamente está autorizado su uso",
    "citando siempre la fuente",
    "licencia de uso",
    "uso autorizado",
    "copyright",
    "queda prohibido su uso sin previa autorizacion expresa",
    "queda prohibido su uso sin previa autorización expresa",
    "la infraccion de estos derechos se perseguira",
    "la infracción de estos derechos se perseguirá",
    "civil y en su caso penalmente",
]


ADMIN_CONTEXT_MARKERS = [
    "advertencia",
    "cuadernillo",
    "modulo de lectura",
    "modulo de razonamiento",
    "modulo de competencias",
    "propiedad exclusiva",
    "marcas registradas",
    "autorizacion expresa",
    "acciones legales",
    "politicas y condiciones",
    "que contiene este cuadernillo",
    "directora general",
    "secretaria general",
    "tomado y adaptado de",
    "saber pro cuadernillo",
]


MOJIBAKE_REPLACEMENTS = {
    "ã¡": "a",
    "ã©": "e",
    "ã­": "i",
    "ã³": "o",
    "ãº": "u",
    "ã±": "n",
    "Ã¡": "a",
    "Ã©": "e",
    "Ã­": "i",
    "Ã³": "o",
    "Ãº": "u",
    "Ã±": "n",
    "â€œ": "",
    "â€": "",
    "â€˜": "",
    "â€™": "",
}


SPANISH_STOPWORDS = {
    "segun", "según", "texto", "siguiente", "cual", "cuál", "opcion", "opción", "correcta", "afirma",
    "sobre", "para", "como", "cómo", "cuando", "donde", "dónde", "quien", "quién", "esta", "este",
    "estos", "estas", "del", "las", "los", "una", "uno", "unos", "unas", "que", "con", "sin", "por",
    "entre", "desde", "hasta", "segun", "según", "respecto", "principal", "idea", "mejor", "resume",
}


ENGLISH_STOPWORDS = {
    "according", "text", "following", "which", "what", "option", "correct", "about", "from", "with",
    "without", "when", "where", "who", "that", "this", "these", "those", "best", "main", "idea",
    "summary", "summarizes", "based", "answer", "question", "statement", "true", "false", "most",
}


def _is_english_competencia(value: str | None) -> bool:
    v = (value or "").strip().lower()
    return v in ("inglés", "ingles", "english")


def _normalize_comp_key(value: str | None) -> str:
    base = str(value or "").strip().lower()
    base = base.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return re.sub(r"\s+", " ", base)


def _plain_text(value: str | None) -> str:
    base = str(value or "").strip().lower()
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        base = base.replace(bad, good)
    base = base.replace("_", " ").replace("-", " ")
    base = base.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return re.sub(r"\s+", " ", base)


def _repair_text_encoding(value: str | None) -> str:
    text = str(value or "")
    if not text:
        return ""
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = text.replace("Â¿", "¿").replace("Â¡", "¡").replace("Â", "")
    return re.sub(r"\s+", " ", text).strip()


COMPETENCIA_CANONICAL = {
    "lectura critica": "Lectura Crítica",
    "razonamiento cuantitativo": "Razonamiento Cuantitativo",
    "comunicacion escrita": "Comunicación Escrita",
    "ingles": "Inglés",
    "ciudadanas": "Ciudadanas",
    "especifica": "Específica",
}


COMPETENCIA_KEYWORDS = {
    "Lectura Crítica": ["lectura critica", "lectura", "critica"],
    "Razonamiento Cuantitativo": ["razonamiento cuantitativo", "cuantitativo", "razonamiento"],
    "Comunicación Escrita": ["comunicacion escrita", "escrita", "comunicacion"],
    "Inglés": ["ingles", "english"],
    "Ciudadanas": ["competencias ciudadanas", "ciudadanas", "ciudadana"],
}


def _canonical_competencia(value: str | None) -> str | None:
    key = _normalize_comp_key(value)
    if not key:
        return None

    for plain, canonical in COMPETENCIA_CANONICAL.items():
        if plain in key:
            return canonical

    if "lectura" in key and "critica" in key:
        return "Lectura Crítica"
    if "razonamiento" in key and "cuantitativo" in key:
        return "Razonamiento Cuantitativo"
    if "comunicacion" in key and "escrita" in key:
        return "Comunicación Escrita"
    if "ingles" in key or "english" in key:
        return "Inglés"
    if "ciudad" in key:
        return "Ciudadanas"
    if "especific" in key:
        return "Específica"

    return None


def _infer_competencia_from_text(value: str | None) -> str | None:
    plain = _plain_text(value)
    if not plain:
        return None

    for canonical, keywords in COMPETENCIA_KEYWORDS.items():
        if any(kw in plain for kw in keywords):
            return canonical
    return None


def _meta_competencia(meta: dict | None) -> str | None:
    source = meta or {}

    explicit = _canonical_competencia(str(source.get("competencia", "")))
    if explicit:
        return explicit

    for field in ("archivo", "fuente", "modulo"):
        inferred = _infer_competencia_from_text(str(source.get(field, "")))
        if inferred:
            return inferred

    return None


def _filter_docs_by_competencia(
    docs: list[str],
    metas: list[dict],
    ids: list[str],
    competencia: str | None,
) -> tuple[list[str], list[dict], list[str]]:
    target = _canonical_competencia(competencia)
    if not target:
        return docs, metas, ids

    filtered_docs: list[str] = []
    filtered_metas: list[dict] = []
    filtered_ids: list[str] = []

    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        doc_id = ids[i] if i < len(ids) else f"unknown_{i}"
        comp = _meta_competencia(meta)
        if comp != target:
            continue
        filtered_docs.append(doc)
        filtered_metas.append(meta)
        filtered_ids.append(doc_id)

    return filtered_docs, filtered_metas, filtered_ids


def _merge_doc_sets(*sets: tuple[list[str], list[dict], list[str]]) -> tuple[list[str], list[dict], list[str]]:
    merged_docs: list[str] = []
    merged_metas: list[dict] = []
    merged_ids: list[str] = []
    seen: set[str] = set()

    for docs, metas, ids in sets:
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            doc_id = ids[i] if i < len(ids) else f"doc_{len(merged_docs)}"
            key = str(doc_id) or _question_fingerprint(doc[:220], str(meta.get("archivo", "")))
            if key in seen:
                continue
            seen.add(key)
            merged_docs.append(doc)
            merged_metas.append(meta)
            merged_ids.append(doc_id)

    return merged_docs, merged_metas, merged_ids


def _is_non_academic_text(value: str | None) -> bool:
    text = _plain_text(value)
    if not text:
        return True

    if any(_plain_text(marker) in text for marker in NON_ACADEMIC_MARKERS):
        return True

    admin_hits = sum(1 for marker in ADMIN_CONTEXT_MARKERS if _plain_text(marker) in text)
    if admin_hits >= 2:
        return True

    if "icfes" in text and any(k in text for k in ("cuadernillo", "modulo", "advertencia")):
        return True

    # Fragmentos que son listados de opciones (A/B/C/D) no sirven como pasaje base.
    if len(re.findall(r"\b[a-d]\.\s", text)) >= 2:
        return True

    return False


# Palabras comunes en español que no existen en inglés — usadas para detectar idioma.
_SPANISH_MARKERS = {
    "tener", "cuenta", "esta", "parte", "definiciones", "pertenecen",
    "sentimientos", "relacionar", "encontraras", "ejemplos", "explicados",
    "respuesta", "importante", "utilizan", "palabras", "modulo",
    "compone", "partes", "pregunta", "siguiente", "texto", "seleccione",
    "opcion", "correcta", "corresponde", "segun", "cual", "siguiente",
    "lectura", "cuadernillo", "evaluacion", "competencia", "responde",
    "acuerdo", "anterior", "afirmacion", "enunciado", "verdadero",
}


def _is_predominantly_spanish(text: str) -> bool:
    """Detecta si un texto es predominantemente en español.
    Usado para rechazar contenido no-inglés en sesiones de inglés."""
    if not text or len(text.strip()) < 20:
        return False
    plain = _plain_text(text)
    words = re.findall(r"[a-záéíóúñü]{3,}", plain)
    if not words:
        return False
    # Contar acentos españoles (á, é, í, ó, ú, ñ, ü) — inglés casi nunca los usa
    accent_count = len(re.findall(r"[áéíóúñü]", plain))
    if accent_count >= 3:
        return True
    # Contar marcadores españoles
    spanish_hits = sum(1 for w in words if w in _SPANISH_MARKERS)
    ratio = spanish_hits / max(1, len(words))
    # Si más del 15% de las palabras son marcadores españoles, es español
    if ratio > 0.15 and spanish_hits >= 3:
        return True
    # Frases enteras que delatan meta-contenido en español
    meta_phrases = [
        "tener en cuenta", "en esta parte", "las definiciones",
        "este modulo", "encontraras ejemplos", "no se utilizan",
        "respuesta correcta", "seleccione la opcion", "de acuerdo con",
    ]
    for phrase in meta_phrases:
        if phrase in plain:
            return True
    return False


def _content_tokens(text: str | None, is_english: bool) -> set[str]:
    plain = _plain_text(text)
    if not plain:
        return set()
    tokens = re.findall(r"[a-záéíóúñ]{3,}", plain)
    stopwords = ENGLISH_STOPWORDS if is_english else SPANISH_STOPWORDS
    return {tok for tok in tokens if tok not in stopwords}


def _is_semantically_aligned(
    texto_base: str,
    enunciado: str,
    respuesta_correcta: str,
    is_english: bool,
) -> bool:
    base_tokens = _content_tokens(texto_base, is_english)
    if len(base_tokens) < 8:
        return False

    q_tokens = _content_tokens(enunciado, is_english)
    # Si el enunciado trae contenido sustantivo, debe compartir al menos 1 término clave con el texto base.
    if len(q_tokens) >= 2 and len(q_tokens & base_tokens) == 0:
        return False

    a_tokens = _content_tokens(respuesta_correcta, is_english)
    # La respuesta correcta también debe anclarse al texto base, salvo respuestas muy cortas.
    if len(a_tokens) >= 2 and len(a_tokens & base_tokens) == 0:
        return False

    return True


def _is_too_literal(texto_base: str, texto_evaluar: str, threshold: float = 0.65) -> bool:
    """Verifica si la respuesta es un copy-paste directo del texto base."""
    if not texto_base or not texto_evaluar:
        return False
        
    # Eliminar prefijo de opción (ej. "A. ", "B. ", "a. ")
    texto_evaluar = re.sub(r"^[A-Za-z][\.\)]\s*", "", str(texto_evaluar)).strip()
        
    eval_clean = re.sub(r"[^\w\s]", "", texto_evaluar.lower()).strip()
    words_eval = eval_clean.split()
    
    # Si la opción es muy corta (ej. una o dos palabras), no sufre de copia literal masiva.
    if len(words_eval) <= 4:
        return False
        
    set_eval = set(words_eval)
    sentences = re.split(r"[.!?\n]+", str(texto_base).lower())
    
    for sent in sentences:
        sent_clean = re.sub(r"[^\w\s]", "", sent).strip()
        words_sent = sent_clean.split()
        if not words_sent:
            continue
            
        # Coincidencia de substring directo
        if eval_clean in sent_clean and len(eval_clean) > 20:
            return True
            
        set_sent = set(words_sent)
        intersection = len(set_eval & set_sent)
        # Si la opción está contenida casi en su totalidad dentro de una sola frase original
        if intersection / len(set_eval) >= threshold:
            return True
            
    return False


def _target_general_mix(cantidad: int) -> dict[str, int]:
    total = max(0, int(cantidad))
    mix = {comp: 0 for comp in GENERAL_COMPETENCIAS_BASE}
    
    if total == 0:
        return mix
        
    has_escrita = "Comunicación Escrita" in GENERAL_COMPETENCIAS_BASE
    if has_escrita and total > 0:
        mix["Comunicación Escrita"] = 1
        total -= 1
        
    remaining_comps = [c for c in GENERAL_COMPETENCIAS_BASE if c != "Comunicación Escrita"]
    if not remaining_comps:
        return mix
        
    base = total // len(remaining_comps)
    rem = total % len(remaining_comps)
    
    for comp in remaining_comps:
        mix[comp] = base
    for idx in range(rem):
        mix[remaining_comps[idx]] += 1
        
    return mix


def _short_comp_code(competencia: str) -> str:
    key = _normalize_comp_key(competencia)
    if "lectura" in key:
        return "LC"
    if "razonamiento" in key:
        return "RC"
    if "comunicacion" in key:
        return "CE"
    if "ingles" in key or "english" in key:
        return "IN"
    if "ciudad" in key:
        return "CC"
    if "especific" in key:
        return "ES"
    return "GN"


def _is_cloze_type(tipo_ingles: str | None) -> bool:
    """Retorna True si el tipo es part4 o part7 (cloze / textos incompletos)."""
    return _normalize_english_type(tipo_ingles) in ("part4", "part7")


def _strip_cloze_markers(text: str) -> str:
    """Elimina marcadores [___], [__N__] de un texto (para Part 5/6 lectura)."""
    cleaned = re.sub(r"\[_+\d*_+\]", "", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _apply_block_structure(items: list[dict], competencia_label: str) -> list[dict]:
    if not items:
        return []

    arranged: list[dict] = []
    cursor = 0
    block_no = 1

    while cursor < len(items):
        remaining = len(items) - cursor
        if remaining >= 4:
            block_size = 3 if block_no % 2 == 1 else 4
        elif remaining == 3:
            block_size = 3
        elif remaining == 2:
            block_size = 2
        else:
            block_size = 1

        if block_size > remaining:
            block_size = remaining

        block_items = [dict(items[cursor + i]) for i in range(block_size)]

        # Solo compartir texto_base entre preguntas del MISMO tipo.
        # Preguntas cloze (part4/part7) NUNCA comparten texto con lectura (part5/part6).
        non_cloze_bases = [
            str(row.get("texto_base", "")).strip()
            for row in block_items
            if str(row.get("texto_base", "")).strip()
            and not _is_cloze_type(str(row.get("tipo_ingles", "")))
        ]
        canonical_base = max(non_cloze_bases, key=len) if non_cloze_bases else ""

        block_id = f"{_short_comp_code(competencia_label)}-{block_no}"
        for idx, row in enumerate(block_items):
            row["competencia"] = competencia_label or str(row.get("competencia") or "General")
            tipo = _normalize_english_type(str(row.get("tipo_ingles", "")))
            is_cloze = tipo in ("part4", "part7")
            is_reading = tipo in ("part5", "part6")

            if is_cloze:
                # Cloze mantiene su propio texto con [___]
                pass
            elif canonical_base:
                # Lectura y otros comparten el canonical_base LIMPIO
                row["texto_base"] = canonical_base

            # Limpiar marcadores [__N__] de preguntas de lectura
            if is_reading and row.get("texto_base"):
                row["texto_base"] = _strip_cloze_markers(str(row["texto_base"]))

            row["bloque_id"] = block_id
            row["orden_en_bloque"] = idx + 1
            row["preguntas_en_bloque"] = block_size
            arranged.append(row)

        cursor += block_size
        block_no += 1

    return arranged


def _build_batch_plan(total: int, max_per_batch: int = 10) -> list[int]:
    plan: list[int] = []
    remaining = max(0, int(total))
    while remaining > 0:
        take = min(max_per_batch, remaining)
        plan.append(take)
        remaining -= take
    return plan


def _repair_text_boundaries(raw_text: str, max_len: int = 1800) -> str:
    text = re.sub(r"\s+", " ", _repair_text_encoding(raw_text)).strip()
    if not text:
        return ""

    if len(text) > max_len:
        text = text[:max_len]

    # Evita arrancar en media frase cuando el chunk comienza en minúscula/símbolo.
    if text and (text[0].islower() or text[0] in ",;:)]"):
        # Prioriza el inicio de la siguiente oración con mayúscula.
        next_sentence = re.search(r"[\.!?]\s+([A-ZÁÉÍÓÚÑ¿¡])", text[:520])
        if next_sentence:
            text = text[next_sentence.start(1):].strip()
        else:
            first_end = re.search(r"[\.!?]\s+", text[:260])
            if first_end:
                candidate = text[first_end.end():].strip()
                if len(candidate.split()) >= 10:
                    text = candidate

    # Evita cortar el final en media frase.
    if text and text[-1] not in ".!?":
        last_end = max(text.rfind("."), text.rfind("?"), text.rfind("!"))
        if last_end >= int(len(text) * 0.55):
            text = text[:last_end + 1].strip()
        else:
            text = text + "."

    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text


def _normalize_text_base_quality(raw_text: str, min_words: int = 30, max_words: int = 230) -> str:
    text = _repair_text_boundaries(raw_text)
    if not text:
        return ""
    if _is_non_academic_text(text):
        return ""

    words = text.split()
    if len(words) < min_words:
        return ""

    if len(words) > max_words:
        text = " ".join(words[:max_words]).strip()
        text = _repair_text_boundaries(text)

    return text


def _compose_fragment_window(docs: list[str], idx: int) -> str:
    current = re.sub(r"\s+", " ", str(docs[idx] or "")).strip()
    if not current:
        return ""

    pieces: list[str] = [current]
    starts_cut = current[0].islower() or current[0] in ",;:)]"
    ends_cut = current[-1] not in ".!?"

    if starts_cut and idx > 0:
        prev_txt = re.sub(r"\s+", " ", str(docs[idx - 1] or "")).strip()
        if prev_txt:
            pieces.insert(0, prev_txt[-800:])

    if ends_cut and idx + 1 < len(docs):
        next_txt = re.sub(r"\s+", " ", str(docs[idx + 1] or "")).strip()
        if next_txt:
            pieces.append(next_txt[:800])

    merged = re.sub(r"\s+", " ", " ".join(pieces)).strip()
    return _repair_text_boundaries(merged, max_len=2400)


def _prepare_fragments(docs: list[str], indices: list[int], min_len: int = 300, is_english: bool = False) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for idx in indices:
        if idx < 0 or idx >= len(docs):
            continue
        text = _compose_fragment_window(docs, idx)
        if len(text) < min_len:
            continue
        if _is_non_academic_text(text):
            continue
        if is_english and _is_predominantly_spanish(text):
            continue

        fingerprint = text[:280].lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        cleaned.append(text)

    return cleaned


def _ensure_count(raw: list[dict], cantidad: int) -> list[dict]:
    if cantidad <= 0:
        return []
    if len(raw) >= cantidad:
        return raw[:cantidad]
    return raw


def _clean_option_text(value: str, index: int) -> str:
    txt = re.sub(r"\s+", " ", _repair_text_encoding(value)).strip()
    txt = re.sub(r"^[A-Da-d][\)\.\:\-]\s*", "", txt)
    letter = ["A", "B", "C", "D"][index]
    if not txt:
        txt = f"Opción {letter}"
    return f"{letter}. {txt}"


def _shuffle_options_with_answer(opciones: list[str], respuesta_correcta: str) -> tuple[list[str], str]:
    if len(opciones) < 4:
        return opciones, respuesta_correcta

    core_options = [re.sub(r"^[A-Da-d]\.\s*", "", str(o or "").strip()) for o in opciones[:4]]
    correct_core = re.sub(r"^[A-Da-d]\.\s*", "", str(respuesta_correcta or "").strip())
    if not correct_core:
        return opciones[:4], opciones[0]

    correct_idx = next((i for i, c in enumerate(core_options) if c.strip().lower() == correct_core.strip().lower()), None)
    if correct_idx is None:
        correct_idx = next((i for i, c in enumerate(core_options) if correct_core.strip().lower() in c.strip().lower()), None)
    if correct_idx is None:
        correct_idx = 0

    order = [0, 1, 2, 3]
    random.shuffle(order)

    shuffled_cores = [core_options[i] for i in order]
    shuffled_options = [_clean_option_text(shuffled_cores[i], i) for i in range(4)]
    new_correct_pos = order.index(correct_idx)
    new_correct = shuffled_options[new_correct_pos]
    return shuffled_options, new_correct


def _answer_index_from_value(opciones: list[str], respuesta_correcta: str) -> int | None:
    letter_match = re.match(r"^\s*([A-Da-d])", str(respuesta_correcta or "").strip())
    if letter_match:
        idx = ord(letter_match.group(1).upper()) - ord("A")
        if 0 <= idx < min(4, len(opciones)):
            return idx

    normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", str(respuesta_correcta or "").strip()).lower()
    for i, opt in enumerate(opciones[:4]):
        normalized_opt = re.sub(r"^[A-Da-d]\.\s*", "", str(opt or "").strip()).lower()
        if normalized_correct and normalized_correct == normalized_opt:
            return i
    for i, opt in enumerate(opciones[:4]):
        normalized_opt = re.sub(r"^[A-Da-d]\.\s*", "", str(opt or "").strip()).lower()
        if normalized_correct and normalized_correct in normalized_opt:
            return i
    return None


def _place_correct_option(opciones: list[str], respuesta_correcta: str, desired_idx: int) -> tuple[list[str], str]:
    if len(opciones) < 4:
        return opciones, respuesta_correcta

    current_idx = _answer_index_from_value(opciones, respuesta_correcta)
    if current_idx is None:
        current_idx = 0

    core = [re.sub(r"^[A-Da-d]\.\s*", "", str(o or "").strip()) for o in opciones[:4]]
    if current_idx != desired_idx:
        core[current_idx], core[desired_idx] = core[desired_idx], core[current_idx]

    relabeled = [_clean_option_text(core[i], i) for i in range(4)]
    return relabeled, relabeled[desired_idx]


def _distribute_answer_letters(raw: list[dict]) -> list[dict]:
    if not raw:
        return []

    pattern = [i % 4 for i in range(len(raw))]
    random.shuffle(pattern)
    balanced: list[dict] = []

    for idx, item in enumerate(raw):
        row = dict(item)
        opciones = _coerce_options(row.get("opciones", []))
        if len(opciones) < 4:
            balanced.append(row)
            continue
        opciones = [_clean_option_text(opciones[i], i) for i in range(4)]
        respuesta = str(row.get("respuesta_correcta", "")).strip()
        fixed_options, fixed_answer = _place_correct_option(opciones, respuesta, pattern[idx])
        row["opciones"] = fixed_options
        row["respuesta_correcta"] = fixed_answer
        balanced.append(row)

    return balanced


def _is_placeholder_option(option_text: str) -> bool:
    core = re.sub(r"^[A-Da-d]\.\s*", "", str(option_text or "").strip()).lower()
    if not core or len(core) < 4:
        return True
    generic_markers = (
        "opcion de respuesta",
        "opción de respuesta",
        "placeholder",
        "respuesta aqui",
        "respuesta aquí",
        "choice",
        "option",
    )
    return any(marker in core for marker in generic_markers)


def _coerce_options(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"\n|\||;", value) if v.strip()]
    return []


def _parse_options_from_meta(meta: dict | None) -> list[str]:
    source = meta or {}

    raw_json = source.get("opciones_json")
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
            if isinstance(parsed, dict):
                out = []
                for letter in ("A", "B", "C", "D"):
                    txt = str(parsed.get(letter, "")).strip()
                    if txt:
                        out.append(f"{letter}. {txt}")
                if out:
                    return out
        except Exception:
            pass

    raw_options = source.get("opciones")
    if isinstance(raw_options, dict):
        out = []
        for letter in ("A", "B", "C", "D"):
            txt = str(raw_options.get(letter, "")).strip()
            if txt:
                out.append(f"{letter}. {txt}")
        if out:
            return out

    raw_string = str(source.get("opciones", "")).strip()
    if raw_string:
        if "||" in raw_string:
            return [v.strip() for v in raw_string.split("||") if v.strip()]
        if raw_string.startswith("[") and raw_string.endswith("]"):
            try:
                parsed = json.loads(raw_string)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            except Exception:
                pass

    return _coerce_options(raw_options)


def _resolve_correct_option_from_meta(opciones: list[str], raw_correct: str) -> str:
    if not opciones:
        return ""

    letter_match = re.match(r"^\s*([A-Da-d])", str(raw_correct or "").strip())
    if letter_match:
        idx = ord(letter_match.group(1).upper()) - ord("A")
        if 0 <= idx < len(opciones):
            return opciones[idx]

    normalized_correct = re.sub(r"^[A-Da-d][\)\.\:\-]\s*", "", str(raw_correct or "").strip()).lower()
    for opt in opciones:
        core = re.sub(r"^[A-Da-d]\.\s*", "", str(opt or "").strip()).lower()
        if normalized_correct and normalized_correct == core:
            return opt
    for opt in opciones:
        core = re.sub(r"^[A-Da-d]\.\s*", "", str(opt or "").strip()).lower()
        if normalized_correct and normalized_correct in core:
            return opt

    return opciones[0]


def _extract_key_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[\.!?])\s+", cleaned)
    for part in parts:
        p = part.strip()
        if len(p.split()) >= 8:
            return p
    return cleaned[:180].strip()


def _extract_topic_hint(text: str, is_english: bool) -> str:
    plain = _plain_text(text)
    if not plain:
        return ""

    words = re.findall(r"[a-záéíóúñ]{4,}", plain)
    stopwords = ENGLISH_STOPWORDS if is_english else SPANISH_STOPWORDS
    for word in words:
        if word not in stopwords:
            return word
    return ""


def _fallback_enunciado(i: int, is_english: bool, topic_hint: str) -> str:
    if is_english:
        starts = [
            "According to the reference text",
            "Based on the passage",
            "From the information provided",
            "In the context of the text",
            "Considering the passage",
            "Given the reference excerpt",
            "After reading the text",
        ]
        verbs = [
            "which option best summarizes",
            "which choice captures",
            "which alternative expresses",
            "which option reflects",
            "which choice synthesizes",
            "which alternative presents",
            "which option states",
            "which choice represents",
        ]
        tails = [
            "the central idea",
            "the main argument",
            "the key message",
            "the principal claim",
            "the overall meaning",
            "the dominant point",
            "the core statement",
            "the main conclusion",
            "the primary focus",
        ]
        stem = f"{starts[i % len(starts)]}, {verbs[i % len(verbs)]} {tails[i % len(tails)]}"
        if topic_hint:
            return f"{stem} about {topic_hint}?"
        return f"{stem}?"

    starts = [
        "Según el texto de referencia",
        "Con base en el pasaje",
        "A partir de la lectura",
        "De acuerdo con la información presentada",
        "En el contexto del texto",
        "Considerando el fragmento",
        "Tras revisar el pasaje",
    ]
    verbs = [
        "¿cuál opción resume mejor",
        "¿qué alternativa sintetiza con mayor precisión",
        "¿cuál opción expresa de forma más clara",
        "¿qué opción refleja mejor",
        "¿qué alternativa representa con mayor fidelidad",
        "¿cuál opción recoge de manera más completa",
        "¿qué alternativa presenta con más precisión",
        "¿cuál opción describe mejor",
    ]
    tails = [
        "la idea principal",
        "el argumento central",
        "el mensaje clave",
        "la tesis dominante",
        "la conclusión principal",
        "el sentido general",
        "la postura central",
        "el enfoque principal",
        "la idea núcleo",
    ]
    stem = f"{starts[i % len(starts)]}, {verbs[i % len(verbs)]} {tails[i % len(tails)]}"
    if topic_hint:
        return f"{stem} sobre {topic_hint}?"
    return f"{stem}?"


def _sentence_pool(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[\.!\?])\s+", cleaned)
    out: list[str] = []
    for p in parts:
        cand = p.strip()
        if len(cand.split()) >= 6:
            out.append(cand)
    return out


def _fallback_option_fillers(is_english: bool, topic_hint: str) -> list[str]:
    if is_english:
        hint = f" regarding {topic_hint}" if topic_hint else ""
        return [
            f"The text focuses on contextual interpretation{hint}.",
            f"The passage emphasizes evidence-based reasoning{hint}.",
            f"The main point combines analysis and justified conclusions{hint}.",
            f"The text highlights coherent argumentation in context{hint}.",
            f"The author prioritizes critical understanding over memorization{hint}.",
        ]

    hint = f" sobre {topic_hint}" if topic_hint else ""
    return [
        f"El texto se centra en interpretación contextual{hint}.",
        f"El pasaje enfatiza razonamiento sustentado en evidencias{hint}.",
        f"La idea principal combina análisis y conclusiones justificadas{hint}.",
        f"El contenido destaca argumentación coherente en contexto{hint}.",
        f"El autor prioriza comprensión crítica sobre memorización literal{hint}.",
    ]


def _ensure_distinct_option_cores(
    candidates: list[str],
    base_text: str,
    is_english: bool,
    topic_hint: str,
) -> list[str]:
    pool = list(candidates)
    pool.extend(_sentence_pool(base_text))
    pool.extend(_fallback_option_fillers(is_english, topic_hint))

    unique: list[str] = []
    seen: set[str] = set()
    for cand in pool:
        c = re.sub(r"\s+", " ", str(cand or "")).strip()
        if not c:
            continue
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
        if len(unique) >= 4:
            break

    while len(unique) < 4:
        seed = len(unique) + 1
        if is_english:
            unique.append(f"Supplementary interpretation statement {seed}.")
        else:
            unique.append(f"Afirmación complementaria de interpretación {seed}.")

    return unique[:4]


def _emergency_academic_passage(competencia_label: str, is_english_session: bool) -> str:
    comp = _normalize_comp_key(competencia_label)
    if is_english_session:
        return (
            "A university launched a tutoring strategy to improve reading outcomes in first-year students. "
            "The plan combined short weekly workshops, guided practice, and formative feedback. "
            "After eight weeks, most students showed better comprehension and greater confidence. "
            "Teachers concluded that frequent feedback and clear goals were the most influential factors."
        )
    if "lectura" in comp:
        return (
            "En una facultad, un grupo de estudiantes analizó dos editoriales sobre el uso de redes sociales en educación. "
            "El primer texto defendía su utilidad para ampliar el acceso a fuentes y ejemplos. "
            "El segundo advertía que el exceso de información sin verificación puede afectar la calidad del aprendizaje. "
            "El debate concluyó que el criterio de lectura y la evaluación de fuentes son condiciones clave para aprovecharlas."
        )
    if "razonamiento" in comp:
        return (
            "Una universidad comparó dos horarios de biblioteca para aumentar el uso estudiantil. "
            "En el horario A se atendieron 240 estudiantes por semana; en el B, 300. "
            "Sin embargo, el costo operativo del horario B fue 20% mayor. "
            "El comité decidió evaluar no solo la cantidad de usuarios, sino también la relación entre beneficio y costo."
        )
    return (
        "En un programa académico se implementó una estrategia de mejora basada en diagnóstico, acompañamiento y evaluación continua. "
        "Los docentes definieron metas de desempeño y los estudiantes recibieron retroalimentación periódica. "
        "Al cierre del periodo, los resultados mostraron avances en comprensión y aplicación de conceptos. "
        "La coordinación concluyó que la consistencia del seguimiento fue determinante para sostener la mejora."
    )


def _build_deterministic_fallback_questions(
    docs: list[str],
    cantidad: int,
    competencia_label: str,
    is_english_session: bool,
    dificultad_objetivo: str | None,
) -> list[dict]:
    if cantidad <= 0 or not docs:
        return []

    reservoir = [_normalize_text_base_quality(d) for d in docs]
    reservoir = [t for t in reservoir if t]
    if not reservoir:
        emergency = _normalize_text_base_quality(_emergency_academic_passage(competencia_label, is_english_session), min_words=30)
        if emergency:
            reservoir = [emergency]
        else:
            return []

    fallback: list[dict] = []
    default_diff = _normalize_difficulty(dificultad_objetivo) or "intermedio"

    for i in range(cantidad):
        base = reservoir[i % len(reservoir)]
        key_correct = _extract_key_sentence(base)
        key_b = _extract_key_sentence(reservoir[(i + 1) % len(reservoir)])
        key_c = _extract_key_sentence(reservoir[(i + 2) % len(reservoir)])
        key_d = _extract_key_sentence(reservoir[(i + 3) % len(reservoir)])

        topic_hint = _extract_topic_hint(base, is_english_session)
        enunciado = _fallback_enunciado(i, is_english_session, topic_hint)

        cores = _ensure_distinct_option_cores(
            [key_correct, key_b, key_c, key_d],
            base_text=base,
            is_english=is_english_session,
            topic_hint=topic_hint,
        )

        opciones = [
            _clean_option_text(cores[0], 0),
            _clean_option_text(cores[1], 1),
            _clean_option_text(cores[2], 2),
            _clean_option_text(cores[3], 3),
        ]
        opciones, respuesta_correcta = _shuffle_options_with_answer(opciones, opciones[0])

        fallback.append({
            "texto_base": base,
            "enunciado": enunciado,
            "opciones": opciones,
            "respuesta_correcta": respuesta_correcta,
            "explicacion": "La opción correcta resume la idea central del texto base presentado.",
            "competencia": competencia_label,
            "tipo_ingles": "reading" if is_english_session else None,
            "nivel_cefr": "A2" if is_english_session else None,
            "nivel_dificultad": None if is_english_session else default_diff,
        })

    return fallback[:cantidad]


def _question_fingerprint(texto_base: str, enunciado: str) -> str:
    tb = _plain_text(texto_base)
    en = _plain_text(enunciado)
    return f"{tb[:220]}|{en[:220]}"


def _dedupe_raw_questions(raw: list[dict], by_competencia: bool = False) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in raw:
        texto_base = str(item.get("texto_base", "") or "")
        enunciado = str(item.get("enunciado", "") or "")
        key = _question_fingerprint(texto_base, enunciado)
        if by_competencia:
            comp_key = _normalize_comp_key(str(item.get("competencia", "") or "General"))
            key = f"{comp_key}|{key}"
        if not key.strip("|"):
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _dedupe_preguntas_by_enunciado(preguntas: list[Pregunta], by_competencia: bool = False) -> list[Pregunta]:
    seen: set[str] = set()
    unique: list[Pregunta] = []
    for pregunta in preguntas:
        key = _plain_text(pregunta.enunciado)
        if by_competencia:
            comp_key = _normalize_comp_key(pregunta.competencia)
            key = f"{comp_key}|{key}"
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(pregunta)
    return unique


def _normalize_generated_questions(
    raw: list[dict],
    default_competencia: str,
    is_english_session: bool,
    dificultad_objetivo: str | None,
) -> list[dict]:
    normalized: list[dict] = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        enunciado = re.sub(r"\s+", " ", str(item.get("enunciado", "")).strip())
        explicacion = re.sub(r"\s+", " ", str(item.get("explicacion", "")).strip())
        competencia = str(item.get("competencia") or default_competencia).strip() or default_competencia

        # Detectar si es pregunta cloze (part4/part7) antes de normalizar texto_base
        raw_tipo = _normalize_english_type(str(item.get("tipo_ingles", "")))
        is_cloze = raw_tipo in ("part4", "part7")

        raw_texto_base = str(item.get("texto_base", "")).strip()
        if is_cloze:
            # Para cloze, usar min_words más bajo para no descartar pasajes con huecos
            texto_base = _normalize_text_base_quality(raw_texto_base, min_words=10)
            if not texto_base:
                texto_base = raw_texto_base  # Preservar el original si normalización lo descarta
        else:
            texto_base = _normalize_text_base_quality(raw_texto_base)

        if not enunciado:
            continue
        if not texto_base:
            texto_base = "Fragmento de entrenamiento ICFES seleccionado para resolver la pregunta."
        if not explicacion:
            explicacion = "La opción correcta está sustentada por el texto base y la competencia evaluada."

        opciones_list = _coerce_options(item.get("opciones"))
        is_escrita = "escrita" in competencia.lower()

        if is_escrita:
            opciones = []
            respuesta_correcta = ""
            item_is_english = False
        else:
            if len(opciones_list) < 4:
                continue
            opciones = [_clean_option_text(opciones_list[i], i) for i in range(4)]
            if any(_is_placeholder_option(opt) for opt in opciones):
                continue
            if len({re.sub(r"^[A-D]\.\s*", "", opt, flags=re.IGNORECASE).strip().lower() for opt in opciones}) < 4:
                continue

            respuesta_raw = str(item.get("respuesta_correcta", "")).strip()
            if not respuesta_raw:
                continue
            respuesta_idx = 0
            
            letter_match = re.match(r"^\s*([A-Da-d])", respuesta_raw)
            if letter_match:
                respuesta_idx = ord(letter_match.group(1).upper()) - ord("A")
            elif respuesta_raw:
                lowered = respuesta_raw.lower()
                found = next((idx for idx, opt in enumerate(opciones) if lowered in opt.lower()), None)
                if found is not None:
                    respuesta_idx = found

            if respuesta_idx < 0 or respuesta_idx > 3:
                continue
            respuesta_correcta = opciones[respuesta_idx]
            opciones, respuesta_correcta = _shuffle_options_with_answer(opciones, respuesta_correcta)
            item_is_english = _is_english_competencia(competencia)

            if not _is_semantically_aligned(texto_base, enunciado, respuesta_correcta, item_is_english):
                continue

            # Anti-literal filter: Si es lectura/general, rechazar opciones que sean copy-paste del texto base
            if not is_cloze and _is_too_literal(texto_base, respuesta_correcta):
                continue


            # Para sesiones de inglés: rechazar preguntas con contenido en español
            if item_is_english:
                if _is_predominantly_spanish(texto_base):
                    continue
                # Verificar que NINGUNA de las opciones esté en español
                spanish_opts = sum(1 for opt in opciones if _is_predominantly_spanish(opt))
                if spanish_opts > 0:
                    continue

            # Post-procesar cloze: asegurar que [___] exista en texto_base para part4/part7
            if is_cloze:
                # Primero: colapsar huecos numerados [__1__], [__2__] etc. a texto normal,
                # excepto dejar UN solo [___] para la respuesta correcta.
                numbered_blanks = list(re.finditer(r"\[_+(\d+)_+\]", texto_base))
                if numbered_blanks:
                    # Quitar todos los marcadores numerados
                    texto_base = re.sub(r"\[_+\d+_+\]", "", texto_base)
                    texto_base = re.sub(r"\s{2,}", " ", texto_base).strip()

                # Si no tiene [___], intentar inyectar buscando la respuesta en el texto
                if "[___]" not in texto_base:
                    answer_word = re.sub(r"^[A-H]\.\s*", "", respuesta_correcta, flags=re.IGNORECASE).strip()
                    if answer_word and len(answer_word) >= 2:
                        # Buscar la palabra en el texto (case-insensitive)
                        pattern = re.compile(re.escape(answer_word), re.IGNORECASE)
                        match = pattern.search(texto_base)
                        if match:
                            texto_base = texto_base[:match.start()] + "[___]" + texto_base[match.end():]

                # Si despues de todo el esfuerzo sigue sin [___], descartar la pregunta
                if "[___]" not in texto_base:
                    continue

            # Limpiar marcadores cloze de preguntas de lectura (Part 5/6)
            if not is_cloze and item_is_english:
                reading_tipo = _normalize_english_type(str(item.get("tipo_ingles", "")))
                if reading_tipo in ("part5", "part6"):
                    texto_base = re.sub(r"\[_+\d*_+\]", "", texto_base)
                    texto_base = re.sub(r"\s{2,}", " ", texto_base).strip()

        if not is_escrita:
            if len(enunciado) < 28:
                continue
            if len(enunciado) > 360:
                continue
            if enunciado.lower().startswith("pregunta") and len(enunciado) < 40:
                continue
            # No descartar preguntas cloze con texto genérico (ya se intentó arreglar arriba)
            if texto_base.lower().startswith("fragmento de entrenamiento") and not is_cloze:
                continue
            if not texto_base:
                continue

        normalized.append({
            "texto_base": texto_base,
            "enunciado": enunciado,
            "opciones": opciones,
            "respuesta_correcta": respuesta_correcta,
            "explicacion": explicacion,
            "competencia": competencia,
            "tipo_ingles": _normalize_english_type(str(item.get("tipo_ingles", ""))) if item_is_english else None,
            "nivel_cefr": _normalize_cefr(str(item.get("nivel_cefr", ""))) if item_is_english else None,
            "nivel_dificultad": _normalize_difficulty(str(item.get("nivel_dificultad", ""))) if not item_is_english else None,
        })

    if not is_english_session:
        default_diff = _normalize_difficulty(dificultad_objetivo) or "intermedio"
        for row in normalized:
            if _is_english_competencia(str(row.get("competencia", ""))):
                continue
            if not row.get("nivel_dificultad"):
                row["nivel_dificultad"] = default_diff

    return normalized


def _rebalance_general_competencies(raw: list[dict], cantidad: int) -> list[dict]:
    if cantidad <= 0:
        return []

    pools: dict[str, list[dict]] = {k: [] for k in GENERAL_COMPETENCIAS_BASE}
    others: list[dict] = []

    for item in raw:
        comp = str(item.get("competencia", "")).strip()
        key = next((k for k in GENERAL_COMPETENCIAS_BASE if k.lower() == comp.lower()), None)
        if key:
            pools[key].append(item)
        else:
            others.append(item)

    base_target = max(1, cantidad // max(1, len(GENERAL_COMPETENCIAS_BASE)))
    selected: list[dict] = []

    for key in GENERAL_COMPETENCIAS_BASE:
        take = pools[key][:base_target]
        selected.extend(take)
        pools[key] = pools[key][base_target:]

    leftovers = []
    for key in GENERAL_COMPETENCIAS_BASE:
        leftovers.extend(pools[key])
    leftovers.extend(others)

    if len(selected) < cantidad:
        selected.extend(leftovers[:cantidad - len(selected)])

    return selected[:cantidad]


def _target_english_mix(cantidad: int) -> dict[str, int]:
    """Distribucion objetivo estilo Saber Pro para modulo de Ingles."""
    if cantidad <= 0:
        return {f"part{i}": 0 for i in range(1, 8)}

    total = max(0, int(cantidad))
    # Saber Pro English Parts distribution
    base = {
        "part1": int(total * 0.10),
        "part2": int(total * 0.10),
        "part3": int(total * 0.15),
        "part4": int(total * 0.15),
        "part5": int(total * 0.15),
        "part6": int(total * 0.15)
    }
    assigned = sum(base.values())
    base["part7"] = max(0, total - assigned)
    return base


def _normalize_english_type(value: str | None) -> str | None:
    if not value:
        return None
    t = value.strip().lower()
    valid_parts = ("part1", "part2", "part3", "part4", "part5", "part6", "part7")
    
    if t in ("reading", "reading_comprehension", "comprension", "comprension_lectora"):
        return "part5"
    if t in ("vocabulary", "vocab", "vocabulary_in_context", "lexico"):
        return "part2"
    if t in ("grammar", "language_use", "uso_gramatical", "gramatica"):
        return "part4"
        
    for part in valid_parts:
        if part in t:
            return part
    return None


def _normalize_cefr(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().upper()
    if v in ("A2", "B1"):
        return v
    return None


def _normalize_difficulty(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in ("basico", "básico"):
        return "basico"
    if v in ("intermedio",):
        return "intermedio"
    if v in ("avanzado",):
        return "avanzado"
    return None


def _balance_english_levels(raw: list[dict], cantidad: int, nivel_objetivo: str | None) -> list[dict]:
    """Favorece preguntas del nivel objetivo sin eliminar completamente la variedad."""
    target = _normalize_cefr(nivel_objetivo)
    if not target or cantidad <= 0:
        return raw[:cantidad]

    target_count = max(1, int(round(cantidad * 0.8)))
    if cantidad >= 5:
        target_count = max(target_count, 4)

    target_items = [item for item in raw if _normalize_cefr(str(item.get("nivel_cefr", ""))) == target]
    other_items = [item for item in raw if item not in target_items]

    selected = target_items[:target_count]
    if len(selected) < cantidad:
        selected.extend(other_items[:cantidad - len(selected)])

    return selected[:cantidad]


def _balance_general_levels(raw: list[dict], cantidad: int, dificultad_objetivo: str | None) -> list[dict]:
    """Favorece dificultad objetivo para competencias generales no-ingles."""
    target = _normalize_difficulty(dificultad_objetivo)
    if not target or cantidad <= 0:
        return raw[:cantidad]

    target_count = max(1, int(round(cantidad * 0.8)))
    if cantidad >= 5:
        target_count = max(target_count, 4)

    target_items = [item for item in raw if _normalize_difficulty(str(item.get("nivel_dificultad", ""))) == target]
    other_items = [item for item in raw if item not in target_items]

    selected = target_items[:target_count]
    if len(selected) < cantidad:
        selected.extend(other_items[:cantidad - len(selected)])

    return selected[:cantidad]


def _balance_english_questions(raw: list[dict], cantidad: int) -> list[dict]:
    """Rebalancea preguntas para asegurar mezcla de part1 a part7."""
    targets = _target_english_mix(cantidad)

    pools: dict[str, list[dict]] = {f"part{i}": [] for i in range(1, 8)}
    others: list[dict] = []

    for item in raw:
        t = _normalize_english_type(str(item.get("tipo_ingles", "")))
        if t in pools:
            pools[t].append(item)
        else:
            others.append(item)

    selected: list[dict] = []
    for t in (f"part{i}" for i in range(1, 8)):
        needed = targets.get(t, 0)
        take = pools[t][:needed]
        selected.extend(take)
        pools[t] = pools[t][needed:]

    leftovers = []
    for t in (f"part{i}" for i in range(1, 8)):
        leftovers.extend(pools[t])
    leftovers.extend(others)

    if len(selected) < cantidad:
        selected.extend(leftovers[:cantidad - len(selected)])

    return selected[:cantidad]


class DatosCuriososRequest(BaseModel):
    programa: str
    competencia: str
    cantidad: int = 8


class AdminAnalyticsRequest(BaseModel):
    task: str
    analytics_context: dict


class ApoyoPreguntaRequest(BaseModel):
    programa: str
    competencia: str
    enunciado: str
    texto_base: str = ""
    opciones: list[str] = []
    explicacion: str = ""


def _generate_questions_sync(fragments: list[str], cantidad: int,
                             competencia: str | None, programa: str, nivel_objetivo: str | None = None,
                             dificultad_objetivo: str | None = None,
                             entrenamiento_general: bool = False) -> list[dict]:
    """
    Llama a Gemini para generar preguntas de selección múltiple
    basadas en fragmentos reales del cuadernillo ICFES.
    """
    comp_label = competencia or "Entrenamiento General Saber Pro"
    is_escrita = "escrita" in comp_label.lower()
    
    if is_escrita:
        context = "[Modo Libre]: Genera un dilema original desafiante (ético, tecnología, laboral, política) para el ensayo."
    else:
        context = "\n\n---\n\n".join(fragments[:5])
        
    is_english = _is_english_competencia(competencia)

    extra_rules = ""
    if is_english:
        mix = _target_english_mix(cantidad)
        target_level = _normalize_cefr(nivel_objetivo) or "A2"
        extra_rules = (
            "\nDISEÑO OBLIGATORIO PARA MÓDULO DE INGLÉS (ESTILO SABER PRO):\n"
            "- Construye una mezcla balanceada de tipos de pregunta siguiendo la estructura de 7 partes.\n"
            f"- Para esta tanda de {cantidad} preguntas, objetivo de mezcla: part1={mix['part1']}, part2={mix['part2']}, part3={mix['part3']}, part4={mix['part4']}, part5={mix['part5']}, part6={mix['part6']}, part7={mix['part7']}.\n"
            f"- Nivel objetivo principal para esta tanda: {target_level}.\n"
            "- Al menos 80% de las preguntas deben coincidir con el nivel objetivo.\n"
            "- Todo enunciado, opciones y texto_base DEBEN estar completamente en inglés.\n"
            "- NUNCA redactes grandes encabezados tipo 'RESPONDE LAS PREGUNTAS 1 A 5'. Genera preguntas individuales.\n"
            "- Cada pregunta DEBE incluir 'tipo_ingles' con uno de estos valores exactos: part1 | part2 | part3 | part4 | part5 | part6 | part7.\n"
            "- REGLAS POR PARTE:\n"
            "  * part1 (Avisos/Señales): 'texto_base' es SOLO EL TEXTO DEL AVISO (ej: 'STAFF ONLY - No entry beyond this point'). 'enunciado' pregunta donde se veria ese aviso. Opciones son diferentes lugares.\n"
            "  * part2 (Vocabulario): 'texto_base' es una definicion o descripcion en ingles. 'opciones' son 4 palabras candidatas.\n"
            "  * part3 (Conversaciones): 'texto_base' va VACIO. 'enunciado' contiene un dialogo corto con un espacio en blanco (ej: 'A: How was your weekend? B: ___').\n"
            "  * part4 (Cloze A2) y part7 (Cloze B1): ATENCION CRITICA — cada pregunta tiene un pasaje en 'texto_base' con EXACTAMENTE UN SOLO marcador [___] (tres guiones bajos entre corchetes). NO USES [__1__], [__2__], etc. SOLO [___]. La respuesta correcta es la palabra que completa ese unico hueco. Si deseas hacer varias preguntas sobre un mismo pasaje, genera cada una como un objeto JSON independiente, cada uno con su propio texto donde el [___] este en una posicion diferente.\n"
            "  * part5 (Comprension literal) y part6 (Comprension inferencial): 'texto_base' es un texto COMPLETO de lectura, SIN NINGUN HUECO ni marcador. 'enunciado' es la pregunta de comprension.\n"
            "    ***CRITICAL RULE FOR PART 5 & 6***: The correct answer MUST BE A PARAPHRASE or SYNTHESIS. NEVER copy and paste a sentence directly from the reference text as the correct answer. LITERAL ANSWERS ARE STRICTLY FORBIDDEN and will cause system failure.\n"
            "- Cada pregunta debe incluir nivel_cefr: A2 | B1.\n"
            "- La respuesta correcta debe estar sustentada por el texto_base.\n"
            "- Organiza la salida en mini-bloques: Part 5/6 pueden compartir texto_base para 2-4 preguntas consecutivas. Part 4/7 NO comparten texto con Part 5/6.\n"
        )
    elif entrenamiento_general:
        extra_rules = (
            "\nDISEÑO OBLIGATORIO PARA ENTRENAMIENTO GENERAL SABER PRO:\n"
            "- Genera un set mixto con distribución equilibrada entre: Lectura Crítica, Razonamiento Cuantitativo, Comunicación Escrita, Inglés y Ciudadanas.\n"
            "- Cada pregunta debe indicar explícitamente su competencia en el campo competencia.\n"
            "- Mantén estilo ICFES: enunciados aplicados, distractores plausibles y una sola respuesta correcta sustentada por texto_base.\n"
            "- texto_base debe ser un pasaje completo y coherente (no frases sueltas), idealmente entre 70 y 180 palabras.\n"
            "- Evita preguntas triviales de memoria; prioriza inferencia, análisis y toma de decisión.\n"
            "- En las preguntas de Inglés, incluir tipo_ingles (part1 a part7) y nivel_cefr (A2|B1).\n"
            "- En preguntas no-inglés, incluir nivel_dificultad (basico|intermedio|avanzado).\n"
            "- Si se menciona gráfico/tabla en el enunciado, el texto_base debe traer los datos textuales suficientes para resolver sin imagen.\n"
            "- Organiza la salida en mini-bloques: cada texto_base debe reutilizarse para 2 a 4 preguntas consecutivas.\n"
        )
    elif is_escrita:
        extra_rules = (
            "\nDISEÑO OBLIGATORIO PARA MÓDULO DE COMUNICACIÓN ESCRITA (ESTILO SABER PRO):\n"
            "- PROHIBIDO GENERAR OPCIONES MÚLTIPLES. DEBEN SER ENSAYOS.\n"
            "- 'opciones' DEBE SER EXACTAMENTE UNA LISTA VACÍA [].\n"
            "- 'respuesta_correcta' DEBE ESTAR VACÍA.\n"
            "- En el campo 'texto_base', construye un DILEMA o SITUACIÓN CONTROVERSIAL de 2 o 3 párrafos (150-250 palabras). El dilema debe mostrar dos o más perspectivas conflictivas sobre un tema de interés público, académico o laboral.\n"
            "- En el campo 'enunciado', proporciona las instrucciones específicas sobre cómo estructurar el ensayo (ej. 'Escribe un texto argumentativo donde asumas una postura frente al dilema expuesto. Justifica tu respuesta...').\n"
        )
    else:
        target_diff = _normalize_difficulty(dificultad_objetivo) or "intermedio"
        extra_rules = (
            "\nDISEÑO OBLIGATORIO PARA COMPETENCIAS GENERALES (NO INGLÉS):\n"
            f"- Nivel de dificultad objetivo para esta tanda: {target_diff}.\n"
            "- Al menos 80% de las preguntas deben coincidir con ese nivel; el resto puede variar para progresion.\n"
            "- Cada pregunta debe incluir nivel_dificultad con uno de estos valores: basico | intermedio | avanzado.\n"
            "- Las preguntas deben ser aplicadas al estilo Saber Pro, con distractores plausibles y contexto suficiente.\n"
            "- Evita memorizacion literal; prioriza analisis, inferencia y toma de decision segun la competencia.\n"
            "- La explicacion debe ser corta, clara y orientada a aprendizaje guiado (sin tono de examen punitivo).\n"
            "- Organiza la salida en mini-bloques: cada texto_base debe reutilizarse para 2 a 4 preguntas consecutivas.\n"
        )

    tipo_pregunta = "dilemas de ensayo libre" if is_escrita else "preguntas de selección múltiple"
    
    if is_escrita:
        reglas_opciones = "- NO HAY OPCIONES. El estudiante escribirá un ensayo."
        formato = f'Formato: [{{"texto_base":"... (dilema extenso) ...","enunciado":"... (instrucciones del ensayo) ...","opciones":[],"respuesta_correcta":"","explicacion":"Se evaluará en base a la rúbrica oficial.","competencia":"{comp_label}","nivel_dificultad":"intermedio"}}]'
    else:
        reglas_opciones = "- 4 opciones por pregunta (A, B, C, D). Solo UNA correcta."
        formato = (f'Formato: [{{"texto_base":"...","enunciado":"...","opciones":["A. ...","B. ...","C. ...","D. ..."],'
                   f'"respuesta_correcta":"A. ...","explicacion":"...","competencia":"{comp_label}",'
                   f'"tipo_ingles":"reading","nivel_cefr":"A2","nivel_dificultad":"intermedio"}}]')

    prompt = (
        f"Eres un experto en la prueba Saber Pro de Colombia (ICFES).\n"
        f"Basándote en temáticas actuales o usando los fragmentos proporcionados como inspiración, "
        f"genera exactamente {cantidad} {tipo_pregunta} para un estudiante "
        f"de {programa} en la competencia de {comp_label}.\n\n"
        f"FRAGMENTOS DEL CUADERNILLO COMO INSPIRACIÓN O BASE:\n{context}\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"{reglas_opciones}\n"
        f"- NUNCA uses fragmentos administrativos/legales/editoriales (derechos, licencias).\n"
        f"- IGNORA COMPLETAMENTE nombres de directores, secretarias, oficinas asesoras, o créditos similares. Si los incluyes en la respuesta, el sistema fallará.\n"
        f"- Si el fragmento principal es una tabla cruda de números o estadísticas (terremotos, habitantes), no la copies y pegues directamente como texto en las opciones de respuesta. Interpreta los datos y ponlos en una pregunta de análisis lógico.\n"
        f"- DEBES DEVOLVER UN JSON ESTRICTO VÁLIDO. NO USES SALTOS DE LÍNEA LITERALES dentro de los textos. Usa '\\n' explícitamente.\n"
        f"- MUY IMPORTANTE: Si necesitas usar comillas dentro de 'texto_base' o 'enunciado', USA COMILLAS SIMPLES (' '). NO USES COMILLAS DOBLES (\") dentro del texto o romperás el JSON.\n"
        f"- texto_base: debe ser extenso (2 o 3 párrafos), mostrando una situación o dilema claro, denso, ético o laboral.\n"
        f"{extra_rules}"
        f"- Devuelve ÚNICAMENTE un array JSON válido, sin markdown.\n\n"
        f"{formato}"
    )
    model = get_gemini_quiz_model()
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    # Limpiar bloque markdown si Gemini lo incluye
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    # Extraer solo el array JSON (por si Gemini añade texto antes/después)
    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            questions = parsed.get("preguntas")
            if isinstance(questions, list):
                return questions
        return []
    except Exception as e:
        print("[AI] Error decoding primary json from Gemini:", e, flush=True)
        try:
            unescaped = (
                text
                .replace('\\"', '"')
                .replace('\\n', ' ')
                .replace('\\[', '[')
                .replace('\\]', ']')
                .replace('\\{', '{')
                .replace('\\}', '}')
            )
            parsed = json.loads(unescaped)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and isinstance(parsed.get("preguntas"), list):
                return parsed.get("preguntas")
        except Exception:
            return []
    return []


def _get_docs(collection, where: dict, limit: int = 200) -> tuple:
    """Ejecuta collection.get() y devuelve (docs, metas, ids) o tupla vacía si falla."""
    try:
        r = collection.get(where=where, include=["documents", "metadatas"], limit=limit)
        return r.get("documents", []), r.get("metadatas", []), r.get("ids", [])
    except Exception:
        return [], [], []


def _get_docs_for_modulo(collection, modulo: str, tipo: str, competencia: str | None = None) -> tuple:
    """
    Busca documentos con cascada de fallbacks:
    1. modulo + tipo + competencia (si existe metadata)
    2. modulo + tipo
    3. solo tipo + filtrado por competencia inferida (archivo/fuente)
    4. solo tipo
    5. sin filtros + filtrado por competencia inferida
    """
    target_comp = _canonical_competencia(competencia)

    if target_comp:
        docs, metas, ids = _get_docs(collection, {"$and": [{"modulo": modulo}, {"tipo": tipo}, {"competencia": target_comp}]})
        if docs:
            return docs, metas, ids

    # Nivel 1: modulo + tipo
    docs, metas, ids = _get_docs(collection, {"$and": [{"modulo": modulo}, {"tipo": tipo}]})
    if docs:
        if target_comp:
            filtered = _filter_docs_by_competencia(docs, metas, ids, competencia)
            if filtered[0]:
                return filtered
        else:
            return docs, metas, ids

    # Nivel 2: solo tipo
    docs, metas, ids = _get_docs(collection, {"tipo": tipo})
    if docs:
        if target_comp:
            filtered = _filter_docs_by_competencia(docs, metas, ids, competencia)
            if filtered[0]:
                return filtered
        else:
            return docs, metas, ids

    # Nivel 3: sin filtros
    docs, metas, ids = _get_docs(collection, {})
    if docs:
        if target_comp:
            filtered = _filter_docs_by_competencia(docs, metas, ids, competencia)
            if filtered[0]:
                return filtered
            return [], [], []
        return docs, metas, ids
    return [], [], []


def _adaptar_a_pregunta(doc: str, meta: dict, doc_id: str,
                        competencia: str | None, programa: str) -> Pregunta:
    """Convierte un fragmento (practica/ejemplo) al modelo Pregunta para el frontend."""
    opciones = _parse_options_from_meta(meta)
    if len(opciones) >= 4:
        opciones = [_clean_option_text(opciones[i], i) for i in range(4)]

    def _extract_labeled_doc_value(text: str, start_label: str, end_label: str | None = None) -> str:
        if not text:
            return ""
        if end_label:
            pattern = rf"{start_label}\s*:\s*(.+?)\s*{end_label}\s*:"
        else:
            pattern = rf"{start_label}\s*:\s*(.+)$"
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        return _repair_text_encoding(re.sub(r"\s+", " ", m.group(1)).strip())

    enunciado_meta = str(meta.get("enunciado", "") or "").strip()

    contexto_meta = str(meta.get("contexto", "") or "").strip()
    if not contexto_meta:
        contexto_meta = _extract_labeled_doc_value(doc, "Contexto", "Enunciado")

    afirmacion_meta = str(meta.get("afirmacion", "") or "").strip()
    if not afirmacion_meta:
        afirmacion_meta = _extract_labeled_doc_value(doc, "Afirmacion", "Contexto")

    if contexto_meta and len(contexto_meta.split()) < 26:
        contexto_doc = _extract_labeled_doc_value(doc, "Contexto", "Enunciado")
        if contexto_doc and len(contexto_doc.split()) > len(contexto_meta.split()):
            contexto_meta = contexto_doc

    if afirmacion_meta:
        contexto_meta = (
            f"{contexto_meta}\n\nEnfoque evaluado: {afirmacion_meta}"
            if contexto_meta
            else f"Enfoque evaluado: {afirmacion_meta}"
        )

    if enunciado_meta and len(contexto_meta.split()) < 18:
        contexto_meta = f"{contexto_meta} Situacion a resolver: {enunciado_meta}".strip()

    texto_base_raw = contexto_meta or doc
    texto_base_min_words = 18 if contexto_meta else 30
    texto_base = _normalize_text_base_quality(texto_base_raw, min_words=texto_base_min_words, max_words=260)
    if not texto_base:
        texto_base = _repair_text_encoding(_repair_text_boundaries(texto_base_raw[:900]))

    enunciado = enunciado_meta or _repair_text_boundaries(doc[:600])

    respuesta_raw = str(meta.get("respuesta_correcta", "") or "").strip()
    respuesta_correcta = _resolve_correct_option_from_meta(opciones, respuesta_raw) if opciones else respuesta_raw

    competencia_value = _meta_competencia(meta) or competencia or "General"

    return Pregunta(
        id=doc_id,
        texto_base=texto_base,
        enunciado=enunciado,
        opciones=opciones,
        respuesta_correcta=respuesta_correcta,
        explicacion=meta.get("explicacion", "Fragmento extraído del cuadernillo oficial ICFES."),
        competencia=competencia_value,
        programa=meta.get("programa", programa),
        tipo_ingles=_normalize_english_type(str(meta.get("tipo_ingles", ""))),
        nivel_cefr=_normalize_cefr(str(meta.get("nivel_cefr", ""))),
        nivel_dificultad=_normalize_difficulty(str(meta.get("nivel_dificultad", ""))),
    )


def _pregunta_to_dict(pregunta: Pregunta) -> dict:
    if hasattr(pregunta, "model_dump"):
        return pregunta.model_dump()
    return pregunta.dict()


def _build_sugerencias_cache_key(
    programa: str,
    competencia: str | None,
    nivel_objetivo: str | None,
    dificultad_objetivo: str | None,
    cantidad: int,
) -> str:
    payload = {
        "programa": (programa or "").strip().lower(),
        "competencia": (competencia or "").strip().lower(),
        "nivel_objetivo": (nivel_objetivo or "").strip().upper(),
        "dificultad_objetivo": (dificultad_objetivo or "").strip().lower(),
        "cantidad": int(cantidad),
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _get_cached_sugerencias(cache_key: str, cantidad: int) -> list[Pregunta] | None:
    now = time.time()
    with _SUGERENCIAS_CACHE_LOCK:
        cached = _SUGERENCIAS_CACHE.get(cache_key)
        if not cached:
            return None
        expires_at, payload = cached
        if expires_at <= now:
            _SUGERENCIAS_CACHE.pop(cache_key, None)
            return None
        snapshot = [dict(item) for item in payload]

    preguntas: list[Pregunta] = []
    for row in snapshot:
        try:
            preguntas.append(Pregunta(**row))
        except Exception:
            continue

    if len(preguntas) < cantidad:
        return None
    return preguntas[:cantidad]


def _set_cached_sugerencias(cache_key: str, preguntas: list[Pregunta]) -> None:
    if not preguntas:
        return

    payload = [_pregunta_to_dict(p) for p in preguntas]
    expires_at = time.time() + SUGERENCIAS_CACHE_TTL_SECONDS

    with _SUGERENCIAS_CACHE_LOCK:
        now = time.time()
        stale_keys = [k for k, (expiry, _) in _SUGERENCIAS_CACHE.items() if expiry <= now]
        for key in stale_keys:
            _SUGERENCIAS_CACHE.pop(key, None)

        while len(_SUGERENCIAS_CACHE) >= SUGERENCIAS_CACHE_MAX_ITEMS:
            oldest_key = next(iter(_SUGERENCIAS_CACHE), None)
            if oldest_key is None:
                break
            _SUGERENCIAS_CACHE.pop(oldest_key, None)

        _SUGERENCIAS_CACHE[cache_key] = (expires_at, payload)


def _ensure_preguntas_count(preguntas: list[Pregunta], cantidad: int, modulo: str) -> list[Pregunta]:
    if cantidad <= 0:
        return []
    if len(preguntas) >= cantidad:
        return preguntas[:cantidad]
    return preguntas


def _merge_seed_with_generated(
    seed: list[Pregunta],
    generated: list[Pregunta],
    cantidad: int,
    entrenamiento_general: bool,
) -> list[Pregunta]:
    if cantidad <= 0:
        return []

    selected: list[Pregunta] = []
    seen_fp: set[str] = set()
    seen_enunciado: set[str] = set()

    def _scoped_fp(p: Pregunta) -> str:
        base = _question_fingerprint(p.texto_base, p.enunciado)
        if entrenamiento_general:
            return f"{_normalize_comp_key(p.competencia)}|{base}"
        return base

    def _scoped_enunciado(p: Pregunta) -> str:
        plain = _plain_text(p.enunciado)
        if not plain:
            return ""
        if entrenamiento_general:
            return f"{_normalize_comp_key(p.competencia)}|{plain}"
        return plain

    for p in (seed or []) + (generated or []):
        if len(selected) >= cantidad:
            break
        is_escrita_item = "escrita" in (p.competencia or "").lower()
        is_ingles_item = "ingl" in (p.competencia or "").lower()
        if is_escrita_item:
            if len(p.opciones) > 0: continue
        elif is_ingles_item:
            if len(p.opciones) < 3: continue
        else:
            if len(p.opciones) < 4: continue

        fp = _scoped_fp(p)
        en = _scoped_enunciado(p)
        if fp in seen_fp or (en and en in seen_enunciado):
            continue

        selected.append(p)
        seen_fp.add(fp)
        if en:
            seen_enunciado.add(en)

    return selected[:cantidad]


def _select_general_mix_from_bank(preguntas: list[Pregunta], cantidad: int) -> list[Pregunta]:
    if cantidad <= 0:
        return []

    target = _target_general_mix(cantidad)
    buckets: dict[str, list[Pregunta]] = {k: [] for k in GENERAL_COMPETENCIAS_BASE}
    leftovers: list[Pregunta] = []

    for pregunta in preguntas:
        comp = _canonical_competencia(pregunta.competencia) or pregunta.competencia
        if comp in buckets:
            buckets[comp].append(pregunta)
        else:
            leftovers.append(pregunta)

    selected: list[Pregunta] = []
    for comp in GENERAL_COMPETENCIAS_BASE:
        take = target.get(comp, 0)
        if take <= 0:
            continue
        selected.extend(buckets[comp][:take])
        buckets[comp] = buckets[comp][take:]

    rest = []
    for comp in GENERAL_COMPETENCIAS_BASE:
        rest.extend(buckets[comp])
    rest.extend(leftovers)

    if len(selected) < cantidad:
        selected.extend(rest[:cantidad - len(selected)])

    return selected[:cantidad]


def _get_curated_bank_questions(
    collection,
    modulo: str,
    programa: str,
    competencia: str | None,
    entrenamiento_general: bool,
    cantidad: int,
) -> list[Pregunta]:
    docs_q, metas_q, ids_q = _get_docs_for_modulo(
        collection,
        modulo,
        "pregunta",
        None if entrenamiento_general else competencia,
    )
    if not docs_q:
        return []

    triples = list(zip(docs_q, metas_q, ids_q))
    random.shuffle(triples)

    bank: list[Pregunta] = []
    for doc, meta, doc_id in triples:
        try:
            pregunta = _adaptar_a_pregunta(
                doc=doc,
                meta=meta,
                doc_id=str(doc_id),
                competencia=competencia,
                programa=programa,
            )
            is_escrita = "escrita" in (pregunta.competencia or "").lower()
            is_ingles_q = _is_english_competencia(pregunta.competencia)
            
            # Forzar a la IA (Gemini) a construir el Inglés desde cero para mapear parts 1-7
            if is_ingles_q:
                continue
            
            if is_escrita:
                if len(pregunta.opciones) > 0:
                    continue
            else:
                if len(pregunta.opciones) < 4:
                    continue
                if not pregunta.respuesta_correcta:
                    continue
                    
            bank.append(pregunta)
        except Exception:
            continue

    bank = _dedupe_preguntas_by_enunciado(bank, by_competencia=entrenamiento_general)
    if not bank:
        return []

    if entrenamiento_general:
        return _select_general_mix_from_bank(bank, cantidad)

    return bank[:cantidad]



def _almacenar_preguntas_db(collection, preguntas: list[Pregunta], modulo: str):
    import time
    if not preguntas:
        return
    docs = []
    metas = []
    ids = []
    timestamp = int(time.time() * 1000)
    for i, p in enumerate(preguntas):
        docs.append(p.json())
        metas.append({
            "modulo": modulo,
            "tipo": "pregunta_generada",
            "competencia": p.competencia or "",
            "programa": p.programa or "",
            "tipo_ingles": p.tipo_ingles or "",
            "nivel_cefr": p.nivel_cefr or "",
            "nivel_dificultad": p.nivel_dificultad or ""
        })
        ids.append(f"gen_ai_{timestamp}_{i}")
    try:
        collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"[{modulo}] ALMACENADAS {len(preguntas)} preguntas en ChromaDB (tipo: pregunta_generada)")
    except Exception as e:
        print(f"[!] Error guardando preguntas AI en ChromaDB: {e}")

def _get_ai_bank_questions(collection, modulo: str, competencia: str | None, entrenamiento_general: bool, cantidad: int, is_english: bool) -> list[Pregunta]:
    docs_q, metas_q, ids_q = _get_docs_for_modulo(
        collection,
        modulo,
        "pregunta_generada",
        None if entrenamiento_general else competencia,
    )
    if not docs_q:
        return []

    import random
    import json
    triples = list(zip(docs_q, metas_q, ids_q))
    random.shuffle(triples)

    bank = []
    for doc, meta, doc_id in triples:
        try:
            parsed = json.loads(doc)
            pregunta = Pregunta(**parsed)
            is_escrita = "escrita" in (pregunta.competencia or "").lower()
            is_ingles = "ingl" in (pregunta.competencia or "").lower()
            if is_escrita:
                if len(pregunta.opciones) > 0:
                    continue
            elif is_ingles:
                if len(pregunta.opciones) < 3:
                    continue
                if not pregunta.respuesta_correcta:
                    continue
            else:
                if len(pregunta.opciones) < 4:
                    continue
                if not pregunta.respuesta_correcta:
                    continue
            bank.append(pregunta)
        except Exception:
            continue

    bank = _dedupe_preguntas_by_enunciado(bank, by_competencia=entrenamiento_general)
    if not bank:
        return []

    if entrenamiento_general:
        return _select_general_mix_from_bank(bank, cantidad)

    if is_english:
        from app.routes.sugerencias import _balance_english_levels, _balance_english_questions
        bank = _balance_english_levels([p.dict() for p in bank], cantidad, None)
        bank = _balance_english_questions(bank, cantidad)
        return [Pregunta(**b) for b in bank][:cantidad]

    return bank[:cantidad]

async def _background_question_miner(
    programa: str, competencia: str | None, nivel_objetivo: str | None,
    dificultad_objetivo: str | None, cantidad: int, entrenamiento_general: bool,
    modulo: str, is_english: bool, comp_meta: str, cache_key: str
):
    # Si es tráfico web (usuario estudiante), solo generamos 2 de fondo para ahorrar API.
    # Si es el script nocturno (empieza por pregen_), respetamos la cuota grande (ej. 45).
    is_pregen = cache_key.startswith("pregen_")
    cantidad_bg = max(cantidad, 45) if is_pregen else 2
    
    print(f"[*] INICIANDO background miner para {modulo} - {comp_meta} (Meta Generación LLM: {cantidad_bg} preguntas)...", flush=True)

    # Evito reescribir variables abajo.
    cantidad = cantidad_bg
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return
    preguntas_seed = [] # Reemplaza el seed q faltaba
    docs_pr, metas_pr, ids_pr = _get_docs_for_modulo(
        collection,
        modulo,
        "practica",
        None if entrenamiento_general else competencia,
    )
    docs_ej, metas_ej, ids_ej = _get_docs_for_modulo(
        collection,
        modulo,
        "ejemplo",
        None if entrenamiento_general else competencia,
    )
    docs, metas, ids = _merge_doc_sets((docs_pr, metas_pr, ids_pr), (docs_ej, metas_ej, ids_ej))
    if "escrita" in (competencia or "").lower():
        docs, metas, ids = [], [], []

    if not docs and "escrita" not in (competencia or "").lower():
        if preguntas_seed:
            _set_cached_sugerencias(cache_key, preguntas_seed)
        return

    loop = asyncio.get_event_loop()
    raw: list[dict] = []
    comp_meta = competencia or "General"

    if entrenamiento_general:
        target_mix = _target_general_mix(cantidad)
        comp_jobs: list[tuple[str, int, list[str], list[dict], list[int], bool]] = []
        comp_tasks = []

        for comp_name in GENERAL_COMPETENCIAS_BASE:
            target_count = target_mix.get(comp_name, 0)
            if target_count <= 0:
                continue

            comp_modulo = get_modulo(programa, comp_name)
            comp_docs_pr, comp_metas_pr, comp_ids_pr = _get_docs_for_modulo(collection, comp_modulo, "practica", comp_name)
            comp_docs_ej, comp_metas_ej, comp_ids_ej = _get_docs_for_modulo(collection, comp_modulo, "ejemplo", comp_name)
            comp_docs, comp_metas, comp_ids = _merge_doc_sets(
                (comp_docs_pr, comp_metas_pr, comp_ids_pr),
                (comp_docs_ej, comp_metas_ej, comp_ids_ej),
            )
            if not comp_docs:
                comp_is_english = _is_english_competencia(comp_name)
                synthetic_seed = [_emergency_academic_passage(comp_name, comp_is_english)]
                comp_raw = _build_deterministic_fallback_questions(
                    docs=synthetic_seed,
                    cantidad=target_count,
                    competencia_label=comp_name,
                    is_english_session=comp_is_english,
                    dificultad_objetivo=dificultad_objetivo,
                )
                comp_raw = _normalize_generated_questions(comp_raw, comp_name, comp_is_english, dificultad_objetivo)
                if comp_is_english:
                    comp_raw = _balance_english_levels(comp_raw, target_count, nivel_objetivo)
                    comp_raw = _balance_english_questions(comp_raw, target_count)
                else:
                    comp_raw = _balance_general_levels(comp_raw, target_count, dificultad_objetivo)
                comp_raw = _apply_block_structure(comp_raw[:target_count], comp_name)
                raw.extend(comp_raw[:target_count])
                continue

            desired_key = _normalize_comp_key(comp_name)
            matching_indices = [
                i for i, m in enumerate(comp_metas)
                if _normalize_comp_key(_meta_competencia(m)) == desired_key
            ]
            if len(matching_indices) >= max(3, target_count // 2):
                pool_indices = matching_indices
            else:
                pool_indices = list(range(len(comp_docs)))
            if not pool_indices:
                continue

            sample_size = min(len(pool_indices), max(target_count * 3, 10))
            if sample_size <= 0:
                continue
            selected_indices = random.sample(pool_indices, sample_size)
            fragments = _prepare_fragments(comp_docs, selected_indices, is_english=_is_english_competencia(comp_name))
            if not fragments:
                fragments = [comp_docs[i] for i in selected_indices]

            comp_jobs.append((
                comp_name,
                target_count,
                comp_docs,
                comp_metas,
                pool_indices,
                _is_english_competencia(comp_name),
            ))
            comp_tasks.append(
                loop.run_in_executor(
                    None,
                    _generate_questions_sync,
                    fragments,
                    target_count,
                    comp_name,
                    programa,
                    nivel_objetivo if _is_english_competencia(comp_name) else None,
                    dificultad_objetivo,
                    False,
                )
            )

        comp_results = await asyncio.gather(*comp_tasks, return_exceptions=True) if comp_tasks else []

        for job, generated in zip(comp_jobs, comp_results):
            comp_name, target_count, comp_docs, comp_metas, pool_indices, comp_is_english = job
            comp_raw: list[dict] = []

            if not isinstance(generated, Exception):
                norm = _normalize_generated_questions(
                    generated,
                    comp_name,
                    comp_is_english,
                    dificultad_objetivo,
                )
                for row in norm:
                    row["competencia"] = comp_name
                comp_raw.extend(norm)

            if len(comp_raw) < target_count:
                missing = target_count - len(comp_raw)
                fallback_raw: list[dict] = []
                fallback_pool = pool_indices if pool_indices else list(range(len(comp_docs)))
                fallback_take = min(len(fallback_pool), missing)
                if fallback_take > 0:
                    for idx in random.sample(fallback_pool, fallback_take):
                        meta = comp_metas[idx] if idx < len(comp_metas) else {}
                        doc = comp_docs[idx]
                        p = _adaptar_a_pregunta(doc=doc, meta=meta, doc_id=f"fallback_{idx}", competencia=comp_name, programa=programa)
                        fallback_raw.append({
                            "texto_base": p.texto_base or doc,
                            "enunciado": p.enunciado,
                            "opciones": p.opciones,
                            "respuesta_correcta": p.respuesta_correcta,
                            "explicacion": p.explicacion,
                            "competencia": comp_name,
                            "tipo_ingles": p.tipo_ingles,
                            "nivel_cefr": p.nivel_cefr,
                            "nivel_dificultad": p.nivel_dificultad,
                        })
                comp_raw.extend(_normalize_generated_questions(fallback_raw, comp_name, comp_is_english, dificultad_objetivo))

            if comp_is_english:
                comp_raw = _balance_english_levels(comp_raw, target_count, nivel_objetivo)
                comp_raw = _balance_english_questions(comp_raw, target_count)
            else:
                comp_raw = _balance_general_levels(comp_raw, target_count, dificultad_objetivo)

            comp_raw = _apply_block_structure(comp_raw[:target_count], comp_name)
            raw.extend(comp_raw[:target_count])

    else:
        batch_jobs: list[str] = []
        batch_tasks = []

        # Oversample: Pedir a Gemini el triple de preguntas para tener un colchón contra los estrictos filtros
        for batch_size in _build_batch_plan(int(cantidad * 3.0), max_per_batch=10):
            sample_size = min(len(docs), max(batch_size * 3, 10))
            indices = random.sample(range(len(docs)), sample_size)
            fragments = _prepare_fragments(docs, indices, is_english=is_english)
            if not fragments:
                fragments = [docs[i] for i in indices]
            batch_comp = str(comp_meta or competencia or "General")
            if metas:
                batch_comp = str(_meta_competencia(metas[indices[0]]) or batch_comp)

            batch_jobs.append(batch_comp)
            batch_tasks.append(
                loop.run_in_executor(
                    None,
                    _generate_questions_sync,
                    fragments,
                    batch_size,
                    competencia,
                    programa,
                    nivel_objetivo,
                    dificultad_objetivo,
                    False,
                )
            )

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True) if batch_tasks else []
        for batch_comp, raw_batch in zip(batch_jobs, batch_results):
            if isinstance(raw_batch, Exception):
                continue
            comp_meta = batch_comp or comp_meta
            raw.extend(_normalize_generated_questions(raw_batch, batch_comp, is_english, dificultad_objetivo))

        if len(raw) < cantidad:
            # Oversample de emergencias
            faltantes = int((cantidad - len(raw)) * 3.0)
            sample_size = min(len(docs), max(faltantes * 3, 10))
            indices = random.sample(range(len(docs)), sample_size)
            fragments = _prepare_fragments(docs, indices, is_english=is_english)
            if not fragments:
                fragments = [docs[i] for i in indices]
            try:
                raw_retry = await loop.run_in_executor(
                    None,
                    _generate_questions_sync,
                    fragments,
                    faltantes,
                    competencia,
                    programa,
                    nivel_objetivo,
                    dificultad_objetivo,
                    False,
                )
                raw.extend(_normalize_generated_questions(raw_retry, str(comp_meta or competencia or "General"), is_english, dificultad_objetivo))
            except Exception:
                pass

        if not raw:
            fallback_size = min(len(docs), cantidad)
            fallback_indices = random.sample(range(len(docs)), fallback_size)
            fallback_raw: list[dict] = []
            for idx in fallback_indices:
                meta = metas[idx] if idx < len(metas) else {}
                doc = docs[idx]
                pregunta = _adaptar_a_pregunta(
                    doc=doc,
                    meta=meta,
                    doc_id=f"fallback_{idx}",
                    competencia=competencia,
                    programa=programa,
                )
                fallback_raw.append({
                    "texto_base": pregunta.texto_base or doc,
                    "enunciado": pregunta.enunciado,
                    "opciones": pregunta.opciones,
                    "respuesta_correcta": pregunta.respuesta_correcta,
                    "explicacion": pregunta.explicacion,
                    "competencia": pregunta.competencia,
                    "tipo_ingles": pregunta.tipo_ingles,
                    "nivel_cefr": pregunta.nivel_cefr,
                    "nivel_dificultad": pregunta.nivel_dificultad,
                })
            raw.extend(_normalize_generated_questions(fallback_raw, str(comp_meta or competencia or "General"), is_english, dificultad_objetivo))

        if is_english:
            raw = _balance_english_levels(raw, cantidad, nivel_objetivo)
            raw = _balance_english_questions(raw, cantidad)
        else:
            raw = _balance_general_levels(raw, cantidad, dificultad_objetivo)

        raw = _apply_block_structure(raw[:cantidad], str(comp_meta or competencia or "General"))

    if entrenamiento_general and len(raw) > cantidad:
        raw = raw[:cantidad]

    if not raw and docs:
        fallback_comp = str(comp_meta or competencia or "General")
        raw.extend(
            _build_deterministic_fallback_questions(
                docs=docs,
                cantidad=cantidad,
                competencia_label=fallback_comp,
                is_english_session=is_english,
                dificultad_objetivo=dificultad_objetivo,
            )
        )

    raw = _dedupe_raw_questions(raw, by_competencia=entrenamiento_general)
    raw = _ensure_count(raw, cantidad)
    raw = _distribute_answer_letters(raw[:cantidad])

    preguntas = []
    for i, item in enumerate(raw[:cantidad]):
        try:
            raw_comp = _repair_text_encoding(str(item.get("competencia", comp_meta)))
            item_comp = _canonical_competencia(raw_comp) or raw_comp or "General"
            item_is_english = _is_english_competencia(item_comp)

            opciones = _coerce_options(item.get("opciones", []))
            is_escr = "escrita" in (item_comp or "General").lower()
            is_ingl = "ingl" in (item_comp or "General").lower()
            if is_escr:
                if len(opciones) > 0: continue
            elif is_ingl:
                if len(opciones) < 3: continue
                opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]
                if any(_is_placeholder_option(opt) for opt in opciones): continue
            else:
                if len(opciones) < 4: continue
                opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                if any(_is_placeholder_option(opt) for opt in opciones): continue

            # Respetar cloze con min_words bajo en segunda pasada
            item_tipo_ingles = _normalize_english_type(str(item.get("tipo_ingles", "")))
            is_item_cloze = item_tipo_ingles in ("part4", "part7")
            raw_tb = str(item.get("texto_base", ""))
            if is_item_cloze:
                texto_base = _normalize_text_base_quality(raw_tb, min_words=10)
                if not texto_base:
                    texto_base = raw_tb.strip()  # Preservar original para cloze
            elif item_tipo_ingles in ("part1", "part2", "part3"):
                texto_base = raw_tb.strip() # Parts 1, 2, 3 have very short or empty text_base!
            else:
                texto_base = _normalize_text_base_quality(raw_tb)

            if not texto_base and item_tipo_ingles != "part3": # Part 3 is expected to be empty
                continue
            if _is_non_academic_text(texto_base):
                continue
            # Safety net: limpiar marcadores de lectura Part 5/6
            if item_tipo_ingles in ("part5", "part6"):
                texto_base = re.sub(r"\[_+\d*_+\]", "", texto_base)
                texto_base = re.sub(r"\s{2,}", " ", texto_base).strip()

            enunciado = re.sub(r"\s+", " ", _repair_text_encoding(str(item.get("enunciado", ""))))
            if len(enunciado) < 28:
                continue
            if len(enunciado) > 360:
                continue

            respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
            is_escrita_flag = "escrita" in (str(item_comp or "General")).lower()
            if not is_escrita_flag and respuesta_correcta not in opciones:
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                respuesta_correcta = matched or (opciones[0] if opciones else "")

            if not _is_semantically_aligned(texto_base, enunciado, respuesta_correcta, item_is_english):
                continue
                
            # Segunda validación anti-literal
            if item_tipo_ingles not in ("part4", "part7") and _is_too_literal(texto_base, respuesta_correcta):
                continue

            # Segunda validación de idioma para inglés
            if item_is_english:
                if _is_predominantly_spanish(texto_base):
                    continue
                spanish_opts_2 = sum(1 for opt in opciones if _is_predominantly_spanish(opt))
                if spanish_opts_2 >= 2:
                    continue

            preguntas.append(Pregunta(
                id=f"gen_{i}_{modulo}",
                texto_base=texto_base,
                enunciado=enunciado,
                opciones=opciones,
                respuesta_correcta=respuesta_correcta,
                explicacion=_repair_text_encoding(str(item.get("explicacion", ""))),
                competencia=item_comp,
                programa=programa,
                tipo_ingles=_normalize_english_type(str(item.get("tipo_ingles", ""))) if item_is_english else None,
                nivel_cefr=_normalize_cefr(str(item.get("nivel_cefr", ""))) if item_is_english else None,
                nivel_dificultad=_normalize_difficulty(str(item.get("nivel_dificultad", ""))) if not item_is_english else None,
                bloque_id=str(item.get("bloque_id") or "").strip() or None,
                orden_en_bloque=int(item.get("orden_en_bloque")) if item.get("orden_en_bloque") is not None else None,
                preguntas_en_bloque=int(item.get("preguntas_en_bloque")) if item.get("preguntas_en_bloque") is not None else None,
            ))
        except Exception:
            continue

    preguntas = _dedupe_preguntas_by_enunciado(preguntas, by_competencia=entrenamiento_general)

    def _fingerprint_with_scope(comp_value: str, texto: str, enunciado_value: str) -> str:
        base_key = _question_fingerprint(texto, enunciado_value)
        if entrenamiento_general:
            return f"{_normalize_comp_key(comp_value)}|{base_key}"
        return base_key

    def _enunciado_with_scope(comp_value: str, enunciado_value: str) -> str:
        plain = _plain_text(enunciado_value)
        if not plain:
            return ""
        if entrenamiento_general:
            return f"{_normalize_comp_key(comp_value)}|{plain}"
        return plain

    if len(preguntas) < cantidad and entrenamiento_general and raw:
        existing_keys: set[str] = set()
        existing_enunciados: set[str] = set()
        for p in preguntas:
            existing_keys.add(_fingerprint_with_scope(p.competencia, p.texto_base, p.enunciado))
            scoped_enunciado = _enunciado_with_scope(p.competencia, p.enunciado)
            if scoped_enunciado:
                existing_enunciados.add(scoped_enunciado)

        next_idx = len(preguntas)
        for item in raw:
            if len(preguntas) >= cantidad:
                break

            try:
                raw_comp = _repair_text_encoding(str(item.get("competencia", comp_meta)))
                item_comp = _canonical_competencia(raw_comp) or raw_comp or "General"
                item_is_english = _is_english_competencia(item_comp)

                texto_base = _normalize_text_base_quality(str(item.get("texto_base", "")))
                if not texto_base:
                    continue

                enunciado = re.sub(r"\s+", " ", _repair_text_encoding(str(item.get("enunciado", ""))))
                if len(enunciado) < 24 or len(enunciado) > 420:
                    continue

                enunciado_key = _enunciado_with_scope(item_comp, enunciado)
                if not enunciado_key or enunciado_key in existing_enunciados:
                    continue

                key = _fingerprint_with_scope(item_comp, texto_base, enunciado)
                if key in existing_keys:
                    continue

                opciones = _coerce_options(item.get("opciones", []))
                is_escr = "escrita" in (item_comp or "General").lower()
                is_ingl = "ingl" in (item_comp or "General").lower()
                if is_escr:
                    if len(opciones) > 0: continue
                elif is_ingl:
                    if len(opciones) < 3: continue
                    opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]
                    if any(_is_placeholder_option(opt) for opt in opciones): continue
                else:
                    if len(opciones) < 4: continue
                    opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                    if any(_is_placeholder_option(opt) for opt in opciones): continue

                respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
                if respuesta_correcta not in opciones:
                    normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                    matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                    respuesta_correcta = matched or opciones[0]

                if not _is_semantically_aligned(texto_base, enunciado, respuesta_correcta, item_is_english):
                    continue

                preguntas.append(Pregunta(
                    id=f"gen_{next_idx}_{modulo}",
                    texto_base=texto_base,
                    enunciado=enunciado,
                    opciones=opciones,
                    respuesta_correcta=respuesta_correcta,
                    explicacion=_repair_text_encoding(str(item.get("explicacion", ""))),
                    competencia=item_comp,
                    programa=programa,
                    tipo_ingles=_normalize_english_type(str(item.get("tipo_ingles", ""))) if item_is_english else None,
                    nivel_cefr=_normalize_cefr(str(item.get("nivel_cefr", ""))) if item_is_english else None,
                    nivel_dificultad=_normalize_difficulty(str(item.get("nivel_dificultad", ""))) if not item_is_english else None,
                    bloque_id=str(item.get("bloque_id") or "").strip() or None,
                    orden_en_bloque=int(item.get("orden_en_bloque")) if item.get("orden_en_bloque") is not None else None,
                    preguntas_en_bloque=int(item.get("preguntas_en_bloque")) if item.get("preguntas_en_bloque") is not None else None,
                ))
                existing_keys.add(key)
                existing_enunciados.add(enunciado_key)
                next_idx += 1
            except Exception:
                continue

    if len(preguntas) < cantidad and entrenamiento_general:
        current_mix = {comp: 0 for comp in GENERAL_COMPETENCIAS_BASE}
        for p in preguntas:
            canonical_comp = _canonical_competencia(p.competencia) or p.competencia
            if canonical_comp in current_mix:
                current_mix[canonical_comp] += 1

        existing_keys: set[str] = set()
        existing_enunciados: set[str] = set()
        for p in preguntas:
            existing_keys.add(_fingerprint_with_scope(p.competencia, p.texto_base, p.enunciado))
            scoped_enunciado = _enunciado_with_scope(p.competencia, p.enunciado)
            if scoped_enunciado:
                existing_enunciados.add(scoped_enunciado)

        next_idx = len(preguntas)
        for comp_name in GENERAL_COMPETENCIAS_BASE:
            if len(preguntas) >= cantidad:
                break

            needed = max(0, target_mix.get(comp_name, 0) - current_mix.get(comp_name, 0))
            if needed <= 0:
                continue

            comp_is_english = _is_english_competencia(comp_name)
            synthetic_seed = [_emergency_academic_passage(comp_name, comp_is_english)]
            synthetic_pool = _build_deterministic_fallback_questions(
                docs=synthetic_seed,
                cantidad=max(needed * 2, needed),
                competencia_label=comp_name,
                is_english_session=comp_is_english,
                dificultad_objetivo=dificultad_objetivo,
            )

            for item in synthetic_pool:
                if len(preguntas) >= cantidad or needed <= 0:
                    break

                try:
                    texto_base = _normalize_text_base_quality(str(item.get("texto_base", "")))
                    enunciado = re.sub(r"\s+", " ", _repair_text_encoding(str(item.get("enunciado", ""))))
                    if not texto_base or not enunciado:
                        continue

                    enunciado_key = _enunciado_with_scope(comp_name, enunciado)
                    if not enunciado_key or enunciado_key in existing_enunciados:
                        continue

                    key = _fingerprint_with_scope(comp_name, texto_base, enunciado)
                    if key in existing_keys:
                        continue

                    opciones = _coerce_options(item.get("opciones", []))
                    is_escr = "escrita" in (comp_name or "General").lower()
                    is_ingl = "ingl" in (comp_name or "General").lower()
                    if is_escr:
                        if len(opciones) > 0: continue
                    elif is_ingl:
                        if len(opciones) < 3: continue
                        opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]
                        if any(_is_placeholder_option(opt) for opt in opciones): continue
                    else:
                        if len(opciones) < 4: continue
                        opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                        if any(_is_placeholder_option(opt) for opt in opciones): continue

                    respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
                    if respuesta_correcta not in opciones:
                        respuesta_correcta = opciones[0]

                    if not _is_semantically_aligned(texto_base, enunciado, respuesta_correcta, comp_is_english):
                        continue

                    if _is_too_literal(texto_base, respuesta_correcta):
                        continue

                    if comp_is_english:
                        if _is_predominantly_spanish(texto_base):
                            continue
                        spanish_opts_fb1 = sum(1 for opt in opciones if _is_predominantly_spanish(opt))
                        if spanish_opts_fb1 > 0:
                            continue

                    preguntas.append(Pregunta(
                        id=f"gen_{next_idx}_{modulo}",
                        texto_base=texto_base,
                        enunciado=enunciado,
                        opciones=opciones,
                        respuesta_correcta=respuesta_correcta,
                        explicacion=_repair_text_encoding(str(item.get("explicacion", ""))),
                        competencia=comp_name,
                        programa=programa,
                        tipo_ingles=_normalize_english_type(str(item.get("tipo_ingles", ""))) if comp_is_english else None,
                        nivel_cefr=_normalize_cefr(str(item.get("nivel_cefr", ""))) if comp_is_english else None,
                        nivel_dificultad=_normalize_difficulty(str(item.get("nivel_dificultad", ""))) if not comp_is_english else None,
                        bloque_id=None,
                        orden_en_bloque=None,
                        preguntas_en_bloque=None,
                    ))
                    existing_keys.add(key)
                    existing_enunciados.add(enunciado_key)
                    current_mix[comp_name] += 1
                    next_idx += 1
                    needed -= 1
                except Exception:
                    continue

    if len(preguntas) < cantidad and docs and not entrenamiento_general:
        existing_keys: set[str] = set()
        existing_enunciados: set[str] = set()
        for p in preguntas:
            existing_keys.add(_fingerprint_with_scope(p.competencia, p.texto_base, p.enunciado))
            scoped_enunciado = _enunciado_with_scope(p.competencia, p.enunciado)
            if scoped_enunciado:
                existing_enunciados.add(scoped_enunciado)
        fallback_comp = str(comp_meta or competencia or "General")
        needed = cantidad - len(preguntas)
        extra_pool = _build_deterministic_fallback_questions(
            docs=docs,
            cantidad=max(needed * 3, needed + 6),
            competencia_label=fallback_comp,
            is_english_session=is_english,
            dificultad_objetivo=dificultad_objetivo,
        )

        next_idx = len(preguntas)
        for item in extra_pool:
            if len(preguntas) >= cantidad:
                break

            try:
                texto_base = _normalize_text_base_quality(str(item.get("texto_base", "")))
                enunciado = re.sub(r"\s+", " ", _repair_text_encoding(str(item.get("enunciado", ""))))
                if not texto_base or not enunciado:
                    continue

                raw_comp = _repair_text_encoding(str(item.get("competencia", fallback_comp)))
                item_comp = _canonical_competencia(raw_comp) or raw_comp or "General"
                item_is_english = _is_english_competencia(item_comp)

                enunciado_key = _enunciado_with_scope(item_comp, enunciado)
                if not enunciado_key or enunciado_key in existing_enunciados:
                    continue

                key = _fingerprint_with_scope(item_comp, texto_base, enunciado)
                if key in existing_keys:
                    continue

                opciones = _coerce_options(item.get("opciones", []))
                is_escr = "escrita" in (item_comp or "General").lower()
                is_ingl = "ingl" in (item_comp or "General").lower()
                if is_escr:
                    if len(opciones) > 0: continue
                elif is_ingl:
                    if len(opciones) < 3: continue
                    opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]
                    if any(_is_placeholder_option(opt) for opt in opciones): continue
                else:
                    if len(opciones) < 4: continue
                    opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                    if any(_is_placeholder_option(opt) for opt in opciones): continue

                respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
                if respuesta_correcta not in opciones:
                    respuesta_correcta = opciones[0]
                if not _is_semantically_aligned(texto_base, enunciado, respuesta_correcta, item_is_english):
                    continue

                if _is_too_literal(texto_base, respuesta_correcta):
                    continue

                if item_is_english:
                    if _is_predominantly_spanish(texto_base):
                        continue
                    spanish_opts_fb2 = sum(1 for opt in opciones if _is_predominantly_spanish(opt))
                    if spanish_opts_fb2 > 0:
                        continue

                preguntas.append(Pregunta(
                    id=f"gen_{next_idx}_{modulo}",
                    texto_base=texto_base,
                    enunciado=enunciado,
                    opciones=opciones,
                    respuesta_correcta=respuesta_correcta,
                    explicacion=_repair_text_encoding(str(item.get("explicacion", ""))),
                    competencia=item_comp,
                    programa=programa,
                    tipo_ingles=_normalize_english_type(str(item.get("tipo_ingles", ""))) if item_is_english else None,
                    nivel_cefr=_normalize_cefr(str(item.get("nivel_cefr", ""))) if item_is_english else None,
                    nivel_dificultad=_normalize_difficulty(str(item.get("nivel_dificultad", ""))) if not item_is_english else None,
                    bloque_id=None,
                    orden_en_bloque=None,
                    preguntas_en_bloque=None,
                ))
                existing_keys.add(key)
                existing_enunciados.add(enunciado_key)
                next_idx += 1
            except Exception:
                continue

    if preguntas_seed:
        preguntas = _merge_seed_with_generated(
            seed=preguntas_seed,
            generated=preguntas,
            cantidad=cantidad,
            entrenamiento_general=entrenamiento_general,
        )

    preguntas = _ensure_preguntas_count(preguntas, cantidad, modulo)
    _set_cached_sugerencias(cache_key, preguntas)
    
    # Store questions properly in ChromaDB so pre_generar_banco.py and future access works.
    try:
        _almacenar_preguntas_db(collection, preguntas, modulo)
        print(f"[{modulo}] EXITO: {len(preguntas)} preguntas almacenadas en DB.", flush=True)
    except Exception as e:
        print(f"[ERROR] Guardando en DB: {e}", flush=True)

@router.post("/datos-curiosos")
async def datos_curiosos(payload: DatosCuriososRequest):
    competencia = payload.competencia or "General"
    cantidad = max(3, min(payload.cantidad, 12))
    facts = await generate_fun_facts(
        programa=payload.programa,
        competencia=competencia,
        cantidad=cantidad,
    )
    return {"datos": facts}


@router.post("/admin-analisis")
async def admin_analisis(payload: AdminAnalyticsRequest):
    analysis = await generate_admin_analytics_report(
        task=payload.task,
        analytics_context=payload.analytics_context,
    )
    return {
        "respuesta": analysis.get("latex", ""),
        "bloques": {
            "resumen": analysis.get("resumen", []),
            "alertas": analysis.get("alertas", []),
            "acciones": analysis.get("acciones", []),
        },
        "documento": analysis.get("documento", {}),
        "meta": analysis.get("analysis_meta", {}),
    }


    if combined:
        _almacenar_preguntas_db(collection, combined, modulo)
    elif 'preguntas' in locals() and preguntas:
        _almacenar_preguntas_db(collection, preguntas, modulo)


@router.get("", response_model=list[Pregunta])
async def sugerencias(
    background_tasks: BackgroundTasks,
    programa: str = QueryParam("General", description="Programa académico del estudiante"),
    competencia: str | None = QueryParam(None, description="Competencia (opcional)"),
    nivel_objetivo: str | None = QueryParam(None, description="Nivel objetivo para Inglés: A2 o B1"),
    dificultad_objetivo: str | None = QueryParam(None, description="Dificultad objetivo para competencias generales: basico/intermedio/avanzado"),
    cantidad: int = QueryParam(15, ge=5, le=30, description="Número de preguntas del entrenamiento"),
):
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return []

    competencia_clean = (competencia or "").strip()
    entrenamiento_general = competencia is None or competencia_clean == "" or competencia_clean.lower() in ("todas", "todos", "general")
    cantidad = max(5, min(cantidad, 30))
    if "escrita" in competencia_clean.lower():
        cantidad = 1

    cache_key = _build_sugerencias_cache_key(
        programa=programa,
        competencia=competencia,
        nivel_objetivo=nivel_objetivo,
        dificultad_objetivo=dificultad_objetivo,
        cantidad=cantidad,
    )
    cached = _get_cached_sugerencias(cache_key, cantidad)
    if cached is not None:
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, get_modulo(programa, None if entrenamiento_general else competencia),
            _is_english_competencia(competencia), competencia or "General", cache_key
        )
        return cached

    modulo = get_modulo(programa, None if entrenamiento_general else competencia)
    is_english = _is_english_competencia(competencia)

    ai_bank = _get_ai_bank_questions(collection, modulo, competencia, entrenamiento_general, cantidad, is_english)
    
    if len(ai_bank) >= cantidad:
        ai_bank = ai_bank[:cantidad]
        _set_cached_sugerencias(cache_key, ai_bank)
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, modulo, is_english, competencia or "General", cache_key
        )
        return ai_bank

    preguntas_curadas = _get_curated_bank_questions(collection, modulo, programa, competencia, entrenamiento_general, cantidad)
    combined = _merge_seed_with_generated(ai_bank, preguntas_curadas, cantidad, entrenamiento_general)
    
    if len(combined) >= cantidad:
        _set_cached_sugerencias(cache_key, combined)
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, modulo, is_english, competencia or "General", cache_key
        )
        return combined

    docs_pr, _, _ = _get_docs_for_modulo(collection, modulo, "practica", None if entrenamiento_general else competencia)
    if docs_pr:
        fallback_pool = _build_deterministic_fallback_questions(docs_pr, cantidad, competencia or "General", is_english, dificultad_objetivo)
        fallback_preguntas = []
        for item in fallback_pool:
            try:
                texto_base = str(item.get("texto_base",""))
                respuesta_correcta = str(item.get("respuesta_correcta",""))
                opciones = item.get("opciones",[])

                if _is_too_literal(texto_base, respuesta_correcta):
                    continue

                if is_english:
                    if _is_predominantly_spanish(texto_base):
                        continue
                    if sum(1 for o in opciones if _is_predominantly_spanish(o)) > 0:
                        continue

                import time
                fallback_preguntas.append(Pregunta(
                    id=f"fb_{int(time.time())}_{len(fallback_preguntas)}",
                    texto_base=str(item.get("texto_base","")),
                    enunciado=str(item.get("enunciado","")),
                    opciones=item.get("opciones",[]),
                    respuesta_correcta=str(item.get("respuesta_correcta","")),
                    explicacion=str(item.get("explicacion","")),
                    competencia=str(item.get("competencia", competencia or "General")),
                    programa=programa,
                    tipo_ingles=str(item.get("tipo_ingles","")) if is_english else None,
                    nivel_cefr=str(item.get("nivel_cefr","")) if is_english else None,
                    nivel_dificultad=str(item.get("nivel_dificultad","")) if not is_english else None
                ))
            except Exception: pass
        combined = _merge_seed_with_generated(combined, fallback_preguntas, cantidad, entrenamiento_general)
    
    if combined:
        _set_cached_sugerencias(cache_key, combined)
    
    background_tasks.add_task(
        _background_question_miner,
        programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
        entrenamiento_general, modulo, is_english, competencia or "General", cache_key
    )
    return combined

@router.post("/apoyo-pregunta")
async def apoyo_pregunta(payload: ApoyoPreguntaRequest):
    support = await generate_practice_support(
        programa=payload.programa,
        competencia=payload.competencia,
        enunciado=payload.enunciado,
        texto_base=payload.texto_base,
        opciones=payload.opciones,
        explicacion=payload.explicacion,
    )
    return support


class EvaluarEnsayoRequest(BaseModel):
    tema: str
    ensayo: str

@router.post("/evaluar-ensayo")
async def evaluar_ensayo_endpoint(payload: EvaluarEnsayoRequest):
    prompt = (
        f"Eres un examinador experto del ICFES para la competencia de 'Comunicación Escrita'.\n"
        f"Evalúa el siguiente ensayo escrito por un estudiante.\n\n"
        f"TEMA DEL ENSAYO: {payload.tema}\n\n"
        f"TEXTO DEL ENSAYO:\n{payload.ensayo}\n\n"
        f"Instrucciones de evaluación:\n"
        f"1. Evalúa basándote en: Planteamiento (tesis), Organización (cohesión/coherencia), y Forma (ortografía/redacción).\n"
        f"2. Asigna un puntaje global entre 0 y 300 puntos.\n"
        f"3. Genera un JSON estricto con las claves: 'puntaje' (int), 'fortalezas' (array de strings), "
        f"'oportunidades' (array de strings), y 'feedback_general' (string breve).\n\n"
        f"Responde ÚNICAMENTE con el formato JSON válido. Sin bloque de markdown extra."
    )
    try:
        model = get_gemini_quiz_model()
        r = model.generate_content(prompt)
        text = (r.text or "").strip()
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx + 1]
        import json
        out = json.loads(text)
        return out
    except Exception as e:
        return {
            "puntaje": 0,
            "fortalezas": ["Error estructural al leer tu ensayo."],
            "oportunidades": ["Contactar soporte técnico."],
            "feedback_general": str(e)
        }


