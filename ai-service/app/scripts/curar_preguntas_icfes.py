"""
Curación inicial de preguntas ICFES (lote piloto) en esquema estructurado JSON.

Objetivo:
- Construir un banco curado con trazabilidad a PDFs oficiales.
- Priorizar ejemplos explicados 2019 para obtener clave y justificación.
- Mantener referencia al cuadernillo base 2018 y al insumo 2021 disponible.

Uso:
    python -m app.scripts.curar_preguntas_icfes --cantidad 5

Salida por defecto:
    data/icfes_docs/general/ejemplos/preguntas_curadas_iniciales_2019_2021.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]

DEFAULT_OUTPUT = ROOT / "data" / "icfes_docs" / "general" / "ejemplos" / "preguntas_curadas_iniciales_2019_2021.json"


@dataclass(frozen=True)
class SourceConfig:
    name: str
    path: Path
    modulo: str
    competencia_default: str
    competencia_map: dict[int, str]
    afirmacion_map: dict[int, str]
    fuente_base_2018: Path | None
    anio: str


RAZONAMIENTO_2019 = SourceConfig(
    name="razonamiento_2019",
    path=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "ejemplos"
    / "Ejemplos_de_preguntas_explicadas_razonamiento_cuantitativo_saber_pro_2019.pdf",
    modulo="general",
    competencia_default="Razonamiento Cuantitativo",
    competencia_map={
        1: "Interpretación y representación",
        2: "Formulación y ejecución",
        3: "Argumentación",
    },
    afirmacion_map={
        1: "Interpreta relaciones cuantitativas en tablas para sustentar conclusiones.",
        2: "Evalúa predicciones en fenómenos aleatorios usando evidencia disponible.",
        3: "Selecciona procedimientos de estimación coherentes con la magnitud solicitada.",
    },
    fuente_base_2018=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "practica"
    / "02_02_Cuadernillo_de_preguntas_razonamiento_cuantitativo_saber_pro_2018.pdf",
    anio="2019",
)

LECTURA_2019 = SourceConfig(
    name="lectura_2019",
    path=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "ejemplos"
    / "Ejemplos_de_preguntas_explicadas_lectura_critica_saber_pro_2019.pdf",
    modulo="general",
    competencia_default="Lectura Crítica",
    competencia_map={
        1: "Comprensión local",
        2: "Comprensión global",
        3: "Reflexión y evaluación",
    },
    afirmacion_map={
        1: "Reconoce la función semántica de conectores y expresiones dentro del argumento.",
        2: "Identifica ideas centrales y relaciones de oposición en textos argumentativos.",
        3: "Deriva inferencias válidas a partir de enunciados explícitos del texto.",
    },
    fuente_base_2018=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "practica"
    / "01_02_Cuadernillo_de_preguntas_Lectura_Critica-_Saber-Pro.pdf",
    anio="2019",
)

CIUDADANAS_2019 = SourceConfig(
    name="ciudadanas_2019",
    path=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "ejemplos"
    / "Ejemplos_de_preguntas_explicadas_competencias_ciudadanas_saber_pro_2019.pdf",
    modulo="general",
    competencia_default="Competencias Ciudadanas",
    competencia_map={
        1: "Conocimientos",
        2: "Pensamiento sistémico",
        3: "Multiperspectivismo",
        4: "Argumentación",
    },
    afirmacion_map={
        1: "Reconoce situaciones de protección o vulneración de derechos en contextos concretos.",
        2: "Analiza conflictos entre dimensiones sociales, ambientales e institucionales.",
        3: "Contrasta posturas de actores con intereses y valores distintos.",
        4: "Evalúa coherencia argumentativa entre una tesis y sus enunciados derivados.",
    },
    fuente_base_2018=ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "practica"
    / "03_02_Cuadernillo_de_preguntas_competencias_ciudadanas_Saber_Pro_2018.pdf",
    anio="2019",
)

ENGLISH_2021_PATH = (
    ROOT
    / "data"
    / "icfes_docs"
    / "general"
    / "ejemplos"
    / "Ejemplos_de_preguntas_explicadas_Ingles_Saber_Pro_2021.pdf"
)

HEADER_LINES = {
    "Saber PRO",
    "Enunciado",
    "Opciones de respuesta",
    "Opciones de respuesta no válidas",
}

OPTION_LABELS = ["A", "B", "C", "D"]

PRIORITY_QUESTION_IDS = [
    "RAZONAMIENTO_2019_Q1",
    "RAZONAMIENTO_2019_Q2",
    "RAZONAMIENTO_2019_Q3",
    "LECTURA_2019_Q2",
    "CIUDADANAS_2019_Q2",
]

MANUAL_OVERRIDES: dict[str, dict[str, Any]] = {
    "RAZONAMIENTO_2019_Q1": {
        "contenido": {
            "contexto": "La tabla resume los sismos del planeta entre 2001 y 2010 por rangos de magnitud (5,0-5,9; 6,0-6,9; 7,0-7,9; 8,0-8,9). En cada año, los eventos de menor magnitud aparecen en cantidades mucho mayores que los de magnitud alta. El análisis debe comparar frecuencia y magnitud, no un dato aislado.",
            "enunciado": "Según el registro histórico, ¿qué relación justifica que en cualquier año sean más probables los sismos de baja magnitud?",
        },
        "solucion": {
            "justificacion_tecnica": "En los registros del contexto, al aumentar la magnitud disminuye la frecuencia observada; la relación correcta es inversa.",
        },
    },
    "RAZONAMIENTO_2019_Q2": {
        "contenido": {
            "contexto": "Con base en el histórico 2001-2010, una persona predice exactamente 173 sismos de magnitud igual o superior a 6,0 para 2011. Los datos muestran variación anual y corresponden a eventos aleatorios; no se presenta una ley determinista que fije un valor exacto para el año siguiente.",
        },
        "solucion": {
            "justificacion_tecnica": "El histórico no permite fijar exactamente un valor futuro para un evento aleatorio; por eso la predicción exacta es incierta.",
        },
    },
    "RAZONAMIENTO_2019_Q3": {
        "contenido": {
            "contexto": "Se dispone del total anual de sismos y se solicita una estimación mensual. La operación debe conservar la unidad temporal (mes), por lo que el total anual debe relacionarse con la cantidad de meses del año, y no con días o con rangos de magnitud.",
            "enunciado": "Las autoridades necesitan estimar la cantidad de sismos mensuales. Una forma correcta de determinar esta frecuencia es:",
        },
        "solucion": {
            "justificacion_tecnica": "Para una frecuencia mensual desde total anual, se divide el total de sismos por año entre los meses del año.",
        },
    },
    "LECTURA_2019_Q2": {
        "contenido": {
            "contexto": "En el texto base, el autor reconoce la crueldad de la lidia, pero cuestiona la coherencia de exigir prohibición mientras se acepta el consumo de carne. Su tesis no es celebrar las corridas, sino problematizar una prohibición presentada sin una consistencia ética general.",
            "enunciado": "De las siguientes ideas, la que se opone a la idea central defendida por el autor es:",
        },
        "solucion": {
            "justificacion_tecnica": "Si la tesis central no defiende la prohibición, la antítesis correcta es la opción que afirma que las corridas deben prohibirse.",
        },
    },
    "CIUDADANAS_2019_Q2": {
        "contenido": {
            "contexto": "Para resolver la basura de la capital, el departamento propone construir un relleno sanitario en un municipio cercano y ofrecer compensación económica. Aunque el proyecto tiene licencias, la comunidad local vota mayoritariamente en contra por riesgos de salud, impacto ambiental y pérdida de valor de la tierra. El conflicto contrapone bienestar sanitario regional y voluntad de la población receptora.",
        },
        "solucion": {
            "justificacion_tecnica": "El caso enfrenta dos intereses legítimos: la salubridad de la capital y la voluntad de los habitantes del municipio donde se proyecta el relleno.",
        },
    },
}


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def _clean_lines(text: str) -> list[str]:
    return [_clean_line(line) for line in text.splitlines() if _clean_line(line)]


def _split_blocks_with_answer(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    prev_end = 0

    for m in re.finditer(r"Respuesta\s+correcta\s*:\s*([A-D])", text, flags=re.IGNORECASE):
        correct = m.group(1).upper()
        qn_match = re.search(r"Pregunta\s*(\d+)", text[m.end() : m.end() + 120], flags=re.IGNORECASE)
        question_num = int(qn_match.group(1)) if qn_match else len(blocks) + 1

        start = text.rfind("Enunciado", prev_end, m.start())
        if start < 0:
            start = prev_end

        next_enunciado = text.find("Enunciado", m.end())
        end_post = next_enunciado if next_enunciado != -1 else len(text)

        block_text = text[start : m.end()]
        post_text = text[m.end() : end_post]

        blocks.append(
            {
                "question_num": question_num,
                "correct": correct,
                "block": block_text,
                "post": post_text,
            }
        )
        prev_end = m.end()

    return blocks


def _group_option_lines(raw_lines: list[str], expected: int = 4) -> list[str]:
    items = [line for line in raw_lines if line and line not in HEADER_LINES]
    if len(items) <= expected:
        return items

    groups: list[str] = []
    current = ""

    for idx, line in enumerate(items):
        remaining_lines = len(items) - idx
        remaining_slots = expected - len(groups)

        if not current:
            current = line
            continue

        # Forzar corte cuando cada línea restante debe ocupar su propio slot.
        if remaining_lines == remaining_slots:
            groups.append(current.strip())
            current = line
            continue

        is_continuation = bool(re.match(r"^[a-záéíóúñ]", line))
        if is_continuation:
            current = f"{current} {line}".strip()
        else:
            groups.append(current.strip())
            current = line

    if current:
        groups.append(current.strip())

    # Balancear al tamaño esperado en caso de sobresegmentación.
    while len(groups) > expected:
        groups[-2] = f"{groups[-2]} {groups[-1]}".strip()
        groups.pop()

    return groups


def _extract_options(lines: list[str], idx_answer: int) -> list[str]:
    idx_a = next((i for i, line in enumerate(lines) if line == "A."), None)

    if idx_a is not None:
        idx_d = next((i for i, line in enumerate(lines[idx_a:], start=idx_a) if line == "D."), idx_a)
        raw = lines[idx_d + 1 : idx_answer]
    else:
        raw = lines[max(0, idx_answer - 10) : idx_answer]

    cleaned = []
    for line in raw:
        if line in HEADER_LINES:
            continue
        if line.lower().startswith("la opción correcta es"):
            continue
        if re.fullmatch(r"[A-D]\.", line):
            continue
        cleaned.append(line)

    grouped = _group_option_lines(cleaned, expected=4)
    options = grouped[-4:]
    if len(options) < 4:
        return []
    return options


def _extract_enunciado_and_context(lines: list[str], idx_answer: int) -> tuple[str, str]:
    idx_a = next((i for i, line in enumerate(lines) if line == "A."), None)
    cut = idx_a if idx_a is not None else max(0, idx_answer - 10)

    pre = lines[:cut]
    filtered = []
    for line in pre:
        if line in HEADER_LINES:
            continue
        if line.lower().startswith("la opción correcta es"):
            continue
        filtered.append(line)

    enunciado = ""
    tail = filtered[-10:]

    for line in reversed(tail):
        if line.startswith("¿"):
            enunciado = line
            break

    if not enunciado:
        for line in reversed(tail):
            if (line.endswith(":") or "?" in line) and len(line.split()) >= 6:
                enunciado = line
                break

    if not enunciado:
        candidates = [line for line in tail if len(line.split()) >= 6]
        if candidates:
            enunciado = candidates[-1]

    if not enunciado and filtered:
        enunciado = filtered[-1]

    context_lines = []
    for line in filtered:
        if line == enunciado:
            break
        context_lines.append(line)

    contexto = " ".join(context_lines[-8:]).strip()
    return enunciado.strip(), contexto


def _extract_justification(post_text: str, correct_letter: str) -> str:
    post_lines = _clean_lines(post_text)
    candidates = []
    for line in post_lines:
        lower = line.lower()
        if lower.startswith("la opción") and ("correcta" in lower or correct_letter.lower() in lower):
            candidates.append(line)

    if candidates:
        return candidates[0]

    for line in post_lines:
        lower = line.lower()
        if line in HEADER_LINES:
            continue
        if re.fullmatch(r"[A-D]", line):
            continue
        if re.fullmatch(r"pregunta\s+\d+", lower):
            continue
        if len(line.split()) >= 10:
            return line

    return (
        f"La alternativa {correct_letter} es la correcta porque mantiene coherencia con el contexto, "
        "la evidencia explícita del enunciado y la competencia evaluada."
    )


def _build_distractor_analysis(correct_letter: str, opciones: dict[str, str], competencia: str) -> dict[str, str]:
    analyses: dict[str, str] = {}
    for letter, text in opciones.items():
        if letter == correct_letter:
            analyses[letter] = "Corresponde con la interpretación más sólida del contexto y el criterio evaluado."
        else:
            analyses[letter] = (
                f"Distractor típico: parece plausible, pero no satisface completamente el criterio de {competencia.lower()} "
                f"ni la evidencia explícita del enunciado."
            )
    return analyses


def _build_question_item(source: SourceConfig, raw_block: dict[str, Any]) -> dict[str, Any] | None:
    qn = int(raw_block["question_num"])
    correct = str(raw_block["correct"]).upper()

    lines = _clean_lines(str(raw_block["block"]))
    idx_answer = next((i for i, line in enumerate(lines) if line.lower().startswith("respuesta correcta:")), None)
    if idx_answer is None:
        return None

    options_raw = _extract_options(lines, idx_answer)
    if len(options_raw) != 4:
        return None

    opciones = {letter: options_raw[idx] for idx, letter in enumerate(OPTION_LABELS)}
    enunciado, contexto = _extract_enunciado_and_context(lines, idx_answer)

    if not enunciado:
        return None

    competencia = source.competencia_map.get(qn, source.competencia_default)
    afirmacion = source.afirmacion_map.get(
        qn,
        "Resuelve la tarea cognitiva del ítem aplicando evidencia explícita del material base.",
    )

    justificacion = _extract_justification(str(raw_block["post"]), correct)
    distractores = _build_distractor_analysis(correct, opciones, competencia)

    pregunta_id = f"{source.name.upper()}_Q{qn}"

    metadatos: dict[str, Any] = {
        "competencia": competencia,
        "afirmacion": afirmacion,
        "fuente": str(source.path.as_posix()),
        "anio_fuente": source.anio,
        "tipo_origen": "ejemplo_explicado",
    }

    if source.fuente_base_2018:
        metadatos["fuente_base_2018"] = str(source.fuente_base_2018.as_posix())

    if ENGLISH_2021_PATH.exists():
        metadatos["fuente_apoyo_2021"] = str(ENGLISH_2021_PATH.as_posix())

    return {
        "pregunta_id": pregunta_id,
        "modulo": source.modulo,
        "metadatos": metadatos,
        "contenido": {
            "contexto": contexto,
            "enunciado": enunciado,
            "opciones": opciones,
        },
        "solucion": {
            "correcta": correct,
            "justificacion_tecnica": justificacion,
            "analisis_distractores": distractores,
        },
    }


def _apply_manual_overrides(item: dict[str, Any]) -> dict[str, Any]:
    pregunta_id = str(item.get("pregunta_id", "")).strip()
    override = MANUAL_OVERRIDES.get(pregunta_id)
    if not override:
        return item

    merged = json.loads(json.dumps(item, ensure_ascii=False))
    for section in ("contenido", "solucion"):
        if section in override and isinstance(override[section], dict):
            merged.setdefault(section, {})
            merged[section].update(override[section])
    return merged


def _extract_from_source(source: SourceConfig) -> list[dict[str, Any]]:
    if not source.path.exists():
        print(f"[WARN] No se encontró fuente: {source.path}")
        return []

    text = _read_pdf_text(source.path)
    blocks = _split_blocks_with_answer(text)
    if not blocks:
        print(f"[WARN] Sin bloques parseables en: {source.path.name}")
        return []

    items: list[dict[str, Any]] = []
    for block in blocks:
        item = _build_question_item(source, block)
        if item:
            items.append(item)

    print(f"[OK] {source.path.name}: {len(items)} preguntas curadas")
    return items


def curar_lote_inicial(cantidad: int) -> list[dict[str, Any]]:
    if cantidad <= 0:
        return []

    sources = [
        RAZONAMIENTO_2019,
        LECTURA_2019,
        CIUDADANAS_2019,
    ]

    curated_all: list[dict[str, Any]] = []
    for source in sources:
        items = _extract_from_source(source)
        curated_all.extend(items)

    curated_all = [_apply_manual_overrides(item) for item in curated_all]
    by_id = {str(item.get("pregunta_id", "")): item for item in curated_all}

    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for pid in PRIORITY_QUESTION_IDS:
        if pid in by_id and pid not in used_ids:
            selected.append(by_id[pid])
            used_ids.add(pid)
        if len(selected) >= cantidad:
            return selected[:cantidad]

    for item in curated_all:
        pid = str(item.get("pregunta_id", ""))
        if pid in used_ids:
            continue
        selected.append(item)
        used_ids.add(pid)
        if len(selected) >= cantidad:
            break

    return selected[:cantidad]


def main() -> None:
    parser = argparse.ArgumentParser(description="Curar preguntas ICFES en JSON estructurado")
    parser.add_argument("--cantidad", type=int, default=5, help="Cantidad de preguntas a exportar")
    parser.add_argument(
        "--salida",
        type=str,
        default=str(DEFAULT_OUTPUT.as_posix()),
        help="Ruta del JSON de salida",
    )
    args = parser.parse_args()

    preguntas = curar_lote_inicial(args.cantidad)

    output_path = Path(args.salida)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "1.0",
        "descripcion": "Lote curado piloto desde PDFs oficiales 2019 con referencia base 2018 y soporte 2021.",
        "fuentes": {
            "2019": [
                str(RAZONAMIENTO_2019.path.as_posix()),
                str(LECTURA_2019.path.as_posix()),
                str(CIUDADANAS_2019.path.as_posix()),
            ],
            "2021": [str(ENGLISH_2021_PATH.as_posix())] if ENGLISH_2021_PATH.exists() else [],
        },
        "preguntas": preguntas,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Preguntas curadas: {len(preguntas)}")
    print(f"[DONE] Salida: {output_path.as_posix()}")


if __name__ == "__main__":
    main()
