"""
Script de indexación de documentos ICFES → ChromaDB.

ESTRUCTURA DE CARPETAS:
    data/icfes_docs/
        general/           ← módulos comunes (Lectura Crítica, Razonamiento Cuantitativo, etc.)
            ejemplos/          PDFs con preguntas EXPLICADAS
            practica/          PDFs con preguntas de práctica
        programas/
            <slug-programa>/   ← módulo ESPECÍFICO de cada carrera
                ejemplos/
                practica/

SLUGS DE PROGRAMAS (sede Fusagasugá):
    administracion-de-empresas
    contaduria-publica
    licenciatura-ciencias-sociales
    ingenieria-electronica
    ingenieria-de-sistemas-y-computacion
    ingenieria-agronomica
    zootecnia
    licenciatura-educacion-fisica

USO:
    # Indexar toda la estructura (general + todos los programas)
    docker exec icfes_ai python -m app.scripts.indexar --raiz data/icfes_docs

    # Solo módulo general
    docker exec icfes_ai python -m app.scripts.indexar \\
        --directorio data/icfes_docs/general --modulo general

    # Módulo específico de un programa
    docker exec icfes_ai python -m app.scripts.indexar \\
        --directorio "data/icfes_docs/programas/ingenieria-de-sistemas-y-computacion" \\
        --modulo ingenieria-de-sistemas-y-computacion

    # Ver estadísticas
    docker exec icfes_ai python -m app.scripts.indexar --stats
"""

import os
import argparse
import hashlib
import json
import re
from pathlib import Path
from collections import Counter

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Configuración ────────────────────────────────────────
CHROMA_HOST     = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "saberpro_docs"
CHUNK_SIZE      = 600
CHUNK_OVERLAP   = 120

# Subcarpetas de tipo dentro de cada módulo
SUBCARPETA_TIPO = {
    "ejemplos": "ejemplo",
    "practica": "practica",
}


def _plain(text: str) -> str:
    s = (text or "").strip().lower()
    s = s.replace("_", " ").replace("-", " ")
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return " ".join(s.split())


def inferir_competencia(nombre_archivo: str, modulo: str) -> str:
    base = _plain(nombre_archivo)
    mod = _plain(modulo)

    if mod != "general":
        return "Específica"

    if "lectura critica" in base or ("lectura" in base and "critica" in base):
        return "Lectura Crítica"
    if "razonamiento cuantitativo" in base or "cuantitativo" in base:
        return "Razonamiento Cuantitativo"
    if "comunicacion escrita" in base or ("comunicacion" in base and "escrita" in base):
        return "Comunicación Escrita"
    if "ingles" in base or "english" in base:
        return "Inglés"
    if "ciudadanas" in base or "ciudadana" in base:
        return "Ciudadanas"
    return "General"


# ── Utilidades ───────────────────────────────────────────


# Señales que indican texto administrativo/introductorio del cuadernillo.
# Un solo hit descarta el chunk — nunca deben entrar a ChromaDB.
_NON_ACADEMIC_CHUNK_SIGNALS = [
    "hoja de respuestas",
    "marque a, b o c",
    "marque a, b, c",
    "en su hoja de",
    "mcer",
    "cefr",
    "guia de orientacion",
    "guía de orientación",
    "marco de referencia disponible",
    "portal web",
    "invitamos a consultar",
    "columna de la derecha",
    "columna de la izquierda",
    "concuerda con cada descripcion",
    "preguntas de seleccion multiple",
    "seleccione la opcion",
    "habilidad especifica relacionada",
    "habilidad específica relacionada",
    "situaciones de evaluacion",
    "situaciones de evaluación",
    "nivel de comprension lectora del evaluado",
    "caracteristicas del modulo",
    "el examen saber pro se compone de modulos",
    "competencias genericas y especificas",
    "marco comun europeo de referencia",
    "instrucciones generales",
    "no escriba en este cuadernillo",
    "llene la hoja de respuestas",
    "terminos y condiciones",
    "derechos de autor",
    "todos los derechos reservados",
    "prohibida su reproduccion",
    "copyright",
    # Solucionarios / claves de respuesta
    "respuesta correcta para la descripcion",
    "opciones de respuesta no validas",
    "no son correctas dado que incluyen",
    "opciones a, b, c, d, e, f",
    "opciones de respuesta conversaciones",
    "muestra la interaccion entre dos personas",
    "primer participante invita al segundo",
    "parte 3 opciones",
    "parte 2 opciones",
    "parte 1 opciones",
    "ninguna otra opcion se ajusta",
    "se refiere a la opcion",
    # Explicaciones del PDF 'Ejemplos de preguntas explicadas'
    "en el texto base el autor",
    "en el texto base, el autor",
    "enfoque evaluado:",
    "identifica ideas centrales",
    "la respuesta correcta es la opcion",
    "las opciones incorrectas",
    "clave de respuesta",
    "justificacion de la respuesta",
    "por que es correcta",
]


def _is_chunk_academic(text: str) -> bool:
    """Devuelve False si el chunk es texto administrativo/introductorio del cuadernillo."""
    normalized = text.lower()
    # Quitar tildes para comparación robusta
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        normalized = normalized.replace(a, b)
    return not any(signal in normalized for signal in _NON_ACADEMIC_CHUNK_SIGNALS)


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 60 and _is_chunk_academic(c)]



def _fix_encoding(text: str) -> str:
    """
    Corrige textos donde PyMuPDF interpreta bytes UTF-8 como CP1252.
    Ej.: 'Ã©' -> 'é', 'Ã³' -> 'ó', 'â€œ' -> '"'
    """
    try:
        fixed = text.encode("cp1252", errors="replace").decode("utf-8", errors="replace")
        def _ruido(t):
            return sum(1 for c in t if c in "Ã\x83\xc3\xc2\ufffd")
        return fixed if _ruido(fixed) < _ruido(text) else text
    except Exception:
        return text


def load_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            pages = [_fix_encoding(page.get_text()) for page in doc]
            doc.close()
            return "\n".join(pages)
        except ImportError:
            print("[Indexar] WARN: pymupdf no disponible.")
            return ""
        except Exception as e:
            print(f"[Indexar] WARN: {path.name}: {e}")
            return ""
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def _clean_line_for_meta(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _normalize_correct_letter(value: str) -> str:
    m = re.match(r"^\s*([A-Da-d])", str(value or "").strip())
    if not m:
        return ""
    return m.group(1).upper()


def _extract_options_list(raw_options) -> list[str]:
    if isinstance(raw_options, dict):
        out = []
        for letter in ("A", "B", "C", "D"):
            txt = _clean_line_for_meta(raw_options.get(letter, ""))
            if txt:
                out.append(f"{letter}. {txt}")
        return out

    if isinstance(raw_options, list):
        out = []
        for i, item in enumerate(raw_options[:4]):
            letter = chr(ord("A") + i)
            txt = _clean_line_for_meta(item)
            txt = re.sub(r"^[A-Da-d][\)\.\:\-]\s*", "", txt)
            if txt:
                out.append(f"{letter}. {txt}")
        return out

    return []


def _resolve_correct_option(correct_raw: str, opciones: list[str]) -> str:
    if not opciones:
        return ""

    letter = _normalize_correct_letter(correct_raw)
    if letter:
        idx = ord(letter) - ord("A")
        if 0 <= idx < len(opciones):
            return opciones[idx]

    normalized_correct = _clean_line_for_meta(correct_raw)
    normalized_correct = re.sub(r"^[A-Da-d][\)\.\:\-]\s*", "", normalized_correct).lower()
    for opt in opciones:
        core = re.sub(r"^[A-Da-d]\.\s*", "", opt).lower()
        if normalized_correct and normalized_correct == core:
            return opt
    for opt in opciones:
        core = re.sub(r"^[A-Da-d]\.\s*", "", opt).lower()
        if normalized_correct and normalized_correct in core:
            return opt

    return opciones[0]


def _build_justification_blob(solucion: dict) -> str:
    justificacion = _clean_line_for_meta(solucion.get("justificacion_tecnica", ""))
    distractores = solucion.get("analisis_distractores", {})
    lines = []
    if justificacion:
        lines.append(f"Justificacion tecnica: {justificacion}")

    if isinstance(distractores, dict):
        for letter in ("A", "B", "C", "D"):
            txt = _clean_line_for_meta(distractores.get(letter, ""))
            if txt:
                lines.append(f"Distractor {letter}: {txt}")

    return "\n".join(lines).strip()


def _parse_question_bank(path: Path) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"[Indexar] WARN: no se pudo leer {path.name}: {e}")
        return []

    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]

    if isinstance(payload, dict):
        if isinstance(payload.get("preguntas"), list):
            return [p for p in payload["preguntas"] if isinstance(p, dict)]
        # Permite indexar un solo objeto pregunta en archivo JSON.
        if "contenido" in payload and "solucion" in payload:
            return [payload]

    return []


def _indexar_question_bank_json(
    collection,
    model,
    file_path: Path,
    modulo: str,
    programa: str,
    fuente_default: str,
    tipo_origen: str,
) -> int:
    preguntas = _parse_question_bank(file_path)
    if not preguntas:
        return 0

    ids, docs, embeddings, metas = [], [], [], []

    for idx, item in enumerate(preguntas, start=1):
        metadatos = item.get("metadatos", {}) if isinstance(item.get("metadatos"), dict) else {}
        contenido = item.get("contenido", {}) if isinstance(item.get("contenido"), dict) else {}
        solucion = item.get("solucion", {}) if isinstance(item.get("solucion"), dict) else {}

        pregunta_id = _clean_line_for_meta(item.get("pregunta_id", f"{file_path.stem}_{idx}"))
        competencia = _clean_line_for_meta(metadatos.get("competencia", "General")) or "General"
        afirmacion = _clean_line_for_meta(metadatos.get("afirmacion", ""))
        fuente = _clean_line_for_meta(metadatos.get("fuente", fuente_default)) or fuente_default

        contexto = _clean_line_for_meta(contenido.get("contexto", ""))
        enunciado = _clean_line_for_meta(contenido.get("enunciado", ""))
        opciones = _extract_options_list(contenido.get("opciones", {}))
        
        is_escrita = "comunicacion" in file_path.name.lower() or "escrita" in file_path.name.lower()
        if is_escrita:
            opciones = []
            correcta = ""
        else:
            min_opts = 3 if ("ingles" in file_path.name.lower() or "english" in file_path.name.lower()) else 4
            if len(opciones) < min_opts:
                continue
            correcta = _resolve_correct_option(str(solucion.get("correcta", "")), opciones)
        explicacion = _build_justification_blob(solucion)

        doc_text = (
            f"Pregunta {pregunta_id}\n"
            f"Competencia: {competencia}\n"
            f"Afirmacion: {afirmacion}\n"
            f"Contexto: {contexto}\n"
            f"Enunciado: {enunciado}\n"
            f"Opciones:\n- " + "\n- ".join(opciones) + "\n"
            f"Respuesta correcta: {correcta}\n"
            f"Explicacion: {explicacion}"
        ).strip()

        if len(doc_text) < 120:
            continue

        doc_id = hashlib.md5(f"{modulo}_pregunta_{file_path.name}_{pregunta_id}".encode()).hexdigest()
        ids.append(doc_id)
        docs.append(doc_text)
        embeddings.append(model.encode(doc_text).tolist())
        metas.append({
            "modulo": modulo,
            "tipo": "pregunta",
            "origen_tipo": tipo_origen,
            "competencia": competencia,
            "afirmacion": afirmacion,
            "fuente": fuente,
            "archivo": file_path.name,
            "programa": programa,
            "pregunta_id": pregunta_id,
            "contexto": contexto,
            "enunciado": enunciado,
            "opciones_json": json.dumps(opciones, ensure_ascii=False),
            "respuesta_correcta": correcta,
            "explicacion": explicacion,
        })

    if not ids:
        return 0

    for i in range(0, len(ids), 50):
        collection.upsert(
            ids=ids[i:i + 50],
            documents=docs[i:i + 50],
            embeddings=embeddings[i:i + 50],
            metadatas=metas[i:i + 50],
        )

    print(f"    {file_path.name}: {len(ids)} preguntas curadas indexadas (tipo=pregunta)")
    return len(ids)


def get_chroma_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Indexación ───────────────────────────────────────────

def indexar_directorio(collection, model, dir_path: Path,
                       modulo: str, programa: str, fuente: str, tipo: str) -> int:
    """
    Indexa todos los PDFs/TXTs de dir_path.
    modulo: 'general' o slug del programa especifico.
    tipo:   'ejemplo' o 'practica'.
    """
    archivos = [f for f in sorted(dir_path.iterdir())
                if f.suffix.lower() in (".pdf", ".txt", ".json") and f.is_file()]
    if not archivos:
        print(f"[Indexar] INFO: Carpeta vacía: {dir_path}")
        return 0

    n_pdf = sum(1 for f in archivos if f.suffix.lower() == ".pdf")
    n_txt = sum(1 for f in archivos if f.suffix.lower() == ".txt")
    n_json = sum(1 for f in archivos if f.suffix.lower() == ".json")
    print(f"\n  [modulo={modulo} | tipo={tipo}] -> {len(archivos)} archivos ({n_pdf} PDF, {n_txt} TXT, {n_json} JSON)")

    ids, docs, embeddings, metas = [], [], [], []
    inserted_from_json = 0
    for file_path in archivos:
        if file_path.suffix.lower() == ".json":
            inserted_from_json += _indexar_question_bank_json(
                collection=collection,
                model=model,
                file_path=file_path,
                modulo=modulo,
                programa=programa,
                fuente_default=fuente,
                tipo_origen=tipo,
            )
            continue

        texto = load_file(file_path)
        if not texto.strip():
            print(f"    WARN: {file_path.name} vacío, se omite.")
            continue
        chunks = chunk_text(texto)
        print(f"    {file_path.name}: {len(chunks)} fragmentos")
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.md5(f"{modulo}_{tipo}_{file_path.name}_{i}".encode()).hexdigest()
            ids.append(doc_id)
            docs.append(chunk)
            embeddings.append(model.encode(chunk).tolist())
            competencia = inferir_competencia(file_path.name, modulo)
            metas.append({
                "modulo":   modulo,
                "tipo":     tipo,
                "competencia": competencia,
                "fuente":   fuente,
                "archivo":  file_path.name,
                "programa": programa,
                "pagina":   str(i + 1),
            })

    if not ids:
        return inserted_from_json

    for i in range(0, len(ids), 50):
        collection.upsert(
            ids=ids[i:i + 50],
            documents=docs[i:i + 50],
            embeddings=embeddings[i:i + 50],
            metadatas=metas[i:i + 50],
        )
    print(f"  OK {len(ids)} fragmentos insertados.")
    return len(ids) + inserted_from_json


def indexar_modulo(collection, model, modulo_path: Path, modulo: str, programa: str) -> int:
    """Indexa las subcarpetas ejemplos/ y practica/ de un directorio de módulo."""
    total = 0
    for subcarpeta, tipo in SUBCARPETA_TIPO.items():
        sub = modulo_path / subcarpeta
        if not sub.exists():
            print(f"[Indexar] INFO: {sub} no existe, se omite.")
            continue
        fuente = f"Cuadernillo {subcarpeta.capitalize()} ICFES [{modulo}]"
        total += indexar_directorio(collection, model, sub,
                                    modulo=modulo, programa=programa,
                                    fuente=fuente, tipo=tipo)
    return total


def mostrar_stats(collection):
    total = collection.count()
    print(f"\n{'='*64}")
    print(f"  COLECCION '{COLLECTION_NAME}'")
    print(f"{'='*64}")
    print(f"  Total fragmentos: {total}")
    if total == 0:
        print("  (sin documentos indexados aun)")
        print(f"{'='*64}\n")
        return

    result = collection.get(limit=min(total, 5000), include=["metadatas"])
    metas_list = result["metadatas"]

    por_modulo   = Counter(m.get("modulo",   "?") for m in metas_list)
    por_tipo     = Counter(m.get("tipo",     "?") for m in metas_list)
    por_archivo  = Counter(m.get("archivo",  "?") for m in metas_list)

    etiquetas_tipo = {
        "ejemplo":  "Ejemplos explicados",
        "practica": "Preguntas de practica",
        "pregunta": "Banco JSON",
    }

    print("\n  Por modulo:")
    for mod, n in sorted(por_modulo.items()):
        tag = " (comun a todos)" if mod == "general" else " (especifico)"
        print(f"    {mod}{tag}: {n} fragmentos")

    print("\n  Por tipo:")
    for tipo, n in sorted(por_tipo.items()):
        print(f"    {etiquetas_tipo.get(tipo, tipo)}: {n} fragmentos")

    print(f"\n  Archivos ({len(por_archivo)}):")
    for arch, n in sorted(por_archivo.items(), key=lambda x: -x[1])[:20]:
        print(f"    - {arch} ({n} frag.)")
    if len(por_archivo) > 20:
        print(f"    ... y {len(por_archivo) - 20} mas")
    print(f"{'='*64}\n")


# ── Main ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Indexar cuadernillos ICFES en ChromaDB")
    parser.add_argument("--raiz",       type=str,
                        help="Carpeta raiz (contiene general/ y programas/)")
    parser.add_argument("--directorio", type=str,
                        help="Directorio de modulo (contiene ejemplos/ y practica/)")
    parser.add_argument("--modulo",     type=str, default="general",
                        help="Slug del modulo: 'general' o nombre-del-programa")
    parser.add_argument("--programa",   type=str, default="General",
                        help="Etiqueta del programa para metadata. Default: General")
    parser.add_argument("--stats",      action="store_true",
                        help="Mostrar estadisticas y salir")
    args = parser.parse_args()

    print(f"[Indexar] Conectando a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}...")
    client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = get_chroma_collection(client)

    if args.stats:
        mostrar_stats(collection)
        return

    print("[Indexar] Cargando modelo all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    total = 0

    if args.raiz:
        raiz = Path(args.raiz)

        # 1. Modulo general (comun a todos los programas)
        general_dir = raiz / "general"
        if general_dir.exists():
            print("\n[Indexar] Modulo GENERAL (Lectura Critica, Razonamiento Cuantitativo, etc.)")
            total += indexar_modulo(collection, model, general_dir,
                                    modulo="general", programa="General")
        else:
            print(f"[Indexar] INFO: {general_dir} no existe, se omite.")

        # 2. Modulos especificos por programa
        programas_dir = raiz / "programas"
        if programas_dir.exists():
            slugs = [d for d in sorted(programas_dir.iterdir()) if d.is_dir()]
            if slugs:
                print(f"\n[Indexar] Modulos ESPECIFICOS ({len(slugs)} programas)")
                for slug_dir in slugs:
                    slug = slug_dir.name
                    print(f"\n[Indexar] Programa: {slug}")
                    total += indexar_modulo(collection, model, slug_dir,
                                            modulo=slug, programa=slug)
            else:
                print("[Indexar] INFO: programas/ existe pero no tiene subcarpetas aun.")
        else:
            print(f"[Indexar] INFO: {programas_dir} no existe, se omiten modulos especificos.")

    elif args.directorio:
        total += indexar_modulo(collection, model, Path(args.directorio),
                                modulo=args.modulo, programa=args.programa)
    else:
        print("[Indexar] Debes usar --raiz, --directorio o --stats.")
        parser.print_help()
        return

    if total == 0:
        print("\nWARN: No se indexo nada. Verifica que las carpetas tengan PDFs o TXTs.")
    else:
        print(f"\nOK Indexacion completa. {total} fragmentos procesados.")
        mostrar_stats(collection)


if __name__ == "__main__":
    main()
