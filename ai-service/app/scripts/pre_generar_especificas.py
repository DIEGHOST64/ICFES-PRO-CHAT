"""
Script de pre-generación de banco de preguntas ESPECÍFICAS por programa.
Autocontenido — no importa de sugerencias.py para evitar side effects.
"""

import sys
import os
import re
import json
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.chroma_client import ChromaService
from app.services.gemini_client import get_gemini_quiz_model
from app.config.especificas_config import (
    PROGRAMA_MODULOS_ESPECIFICOS,
    get_modulos_for_programa,
)

# ─── Settings ───
BATCH_SIZE = 8      # Preguntas por llamada a Gemini
NUM_BATCHES = 4     # Batches por módulo → ~32 crudas, ~20 tras filtros
MIN_TARGET = 30     # Mínimo de preguntas por programa


def _repair_latex_json(raw: str) -> str:
    text = raw
    latex_commands = [
        "frac", "binom", "sqrt", "times", "cdot", "Delta", "theta",
        "alpha", "beta", "gamma", "pi", "sigma", "lambda", "mu",
        "sum", "prod", "int", "infty", "partial", "nabla", "approx",
        "Rightarrow", "Leftrightarrow", "longrightarrow", "text",
        "textbf", "textit", "overline", "underline", "bar", "hat",
        "pm", "div", "neq", "leq", "geq", "equiv", "sim", "propto",
        "subseteq", "supseteq", "in", "notin", "forall", "exists",
        "cup", "cap", "emptyset", "angle", "triangle",
    ]
    for cmd in latex_commands:
        text = text.replace(f"\\{cmd}", f"\\\\{cmd}")
    return text


def _generate_batch(cantidad: int, programa: str, modulo_config: dict, dificultad: str = "intermedio") -> list[dict]:
    """Genera un batch de preguntas llamando a Gemini directamente."""
    nombre_modulo = modulo_config["nombre"]
    temas = modulo_config.get("temas", [])
    requiere_tabla = modulo_config.get("requiere_tabla", False)
    requiere_latex = modulo_config.get("requiere_latex", False)
    ejemplo_tabla = modulo_config.get("ejemplo_tabla", "")

    temas_str = "\n".join(f"  - {t}" for t in temas)

    tabla_instrucciones = ""
    if requiere_tabla and ejemplo_tabla:
        tabla_instrucciones = (
            "\n- OBLIGATORIO: Al menos el 60% de las preguntas DEBEN incluir una tabla Markdown en el texto_base.\n"
            "- La tabla debe presentar datos numéricos reales y coherentes que el estudiante debe analizar.\n"
            "- NO uses imágenes — representa TODA la información como texto y tablas Markdown.\n"
            f"- EJEMPLO DE TABLA:\n{ejemplo_tabla}\n"
        )
    elif requiere_tabla:
        tabla_instrucciones = (
            "\n- Incluye tablas Markdown con datos cuando el tema lo requiera.\n"
            "- NO uses imágenes — representa TODA la información como texto y tablas Markdown.\n"
        )

    latex_instrucciones = ""
    if requiere_latex:
        latex_instrucciones = (
            "\n- Si el tema requiere fórmulas, inclúyelas en notación LaTeX inline: $V = IR$\n"
        )

    prompt = (
        f"Eres un diseñador experto de evaluaciones para Saber Pro, módulo específico '{nombre_modulo}'.\n"
        f"Genera exactamente {cantidad} preguntas de selección múltiple para un estudiante de {programa}.\n\n"
        f"MÓDULO: {nombre_modulo}\n"
        f"PROGRAMA: {programa}\n"
        f"TEMAS VÁLIDOS:\n{temas_str}\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"- 4 opciones por pregunta (A, B, C, D). Solo UNA correcta.\n"
        f"- texto_base: Un CASO DE ESTUDIO de 80-180 palabras que presente una situación profesional realista.\n"
        f"- El caso debe ser específico del área de {programa}, no genérico.\n"
        f"- enunciado: Pregunta que exija ANÁLISIS del caso (no memorización pura).\n"
        f"- Las opciones deben ser plausibles y profesionalmente redactadas.\n"
        f"- explicacion: Justificación técnica clara de 2-3 oraciones.\n"
        f"- Nivel de dificultad: {dificultad}. Incluir campo nivel_dificultad.\n"
        f"- competencia: DEBE ser exactamente 'Específica'.\n"
        f"- Incluir campo modulo_especifico con el valor '{nombre_modulo}'.\n"
        f"{tabla_instrucciones}"
        f"{latex_instrucciones}"
        f"- Evita preguntas triviales de definición pura; prioriza aplicación, análisis y toma de decisiones.\n"
        f"- PROHIBIDO incluir frases conversacionales (ej: 'Aquí tienes...', 'Te presento...'). Solo contenido académico.\n"
        f"- DEBES DEVOLVER UN JSON ESTRICTO VÁLIDO. NO USES saltos de línea literales; usa '\\n' para los saltos de línea en las tablas Markdown.\n"
        f"- CRITICO PARA LaTeX: ESCAPA TODAS las barras invertidas. Ej: escribe \\\\frac en lugar de \\frac.\n"
        f"- MUY IMPORTANTE: Si necesitas usar comillas dentro del texto, USA COMILLAS SIMPLES (' ').\n"
        f"- Devuelve ÚNICAMENTE un array JSON válido, sin markdown ni texto adicional.\n\n"
        f'Formato: [{{"texto_base":"...","enunciado":"...","opciones":["A. ...","B. ...","C. ...","D. ..."],'
        f'"respuesta_correcta":"A. ...","explicacion":"...","competencia":"Específica",'
        f'"modulo_especifico":"{nombre_modulo}","nivel_dificultad":"{dificultad}"}}]'
    )

    model = get_gemini_quiz_model()
    response = model.generate_content(prompt)
    text = (response.text or "").strip()

    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception:
        try:
            unescaped = text.replace('\\"', '"')
            parsed = json.loads(unescaped)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        try:
            repaired = _repair_latex_json(text)
            parsed = json.loads(repaired)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []
    except Exception:
        try:
            unescaped = text.replace('\\"', '"')
            parsed = json.loads(unescaped)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        try:
            repaired = _repair_latex_json(text)
            parsed = json.loads(repaired)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []


def _filter_and_build(all_raw: list[dict], programa: str) -> list[dict]:
    """Filtra preguntas crudas y devuelve las que pasan calidad."""
    valid = []
    seen_enunciados = set()
    for i, item in enumerate(all_raw):
        try:
            opciones = item.get("opciones", [])
            if not isinstance(opciones, list) or len(opciones) < 4:
                continue

            # Limpiar opciones
            clean_opciones = []
            for j, opt in enumerate(opciones[:4]):
                opt = str(opt).strip()
                letter = chr(65 + j)
                if not re.match(r'^[A-Da-d]\.', opt):
                    opt = f"{letter}. {opt}"
                clean_opciones.append(opt)

            texto_base = str(item.get("texto_base", "")).strip()
            if not texto_base or len(texto_base) < 40:
                continue

            enunciado = str(item.get("enunciado", "")).strip()
            # Collapse spaces but preserve newlines softly if any
            enunciado = re.sub(r"[ \t]+", " ", enunciado).strip()
            if len(enunciado) < 28:
                continue

            # Dedup por enunciado
            enunciado_key = enunciado.lower()[:80]
            if enunciado_key in seen_enunciados:
                continue
            seen_enunciados.add(enunciado_key)

            respuesta_correcta = str(item.get("respuesta_correcta", "")).strip()
            if respuesta_correcta not in clean_opciones:
                # Intentar match parcial
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next(
                    (opt for opt in clean_opciones if normalized_correct and
                     normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()),
                    None,
                )
                respuesta_correcta = matched or clean_opciones[0]

            valid.append({
                "texto_base": texto_base,
                "enunciado": enunciado,
                "opciones": clean_opciones,
                "respuesta_correcta": respuesta_correcta,
                "explicacion": str(item.get("explicacion", "Respuesta sustentada por análisis técnico.")),
                "competencia": "Específica",
                "programa": programa,
                "modulo_especifico": str(item.get("modulo_especifico", "")),
                "nivel_dificultad": str(item.get("nivel_dificultad", "intermedio")),
            })
        except Exception:
            continue
    return valid


def _store_questions(collection, questions: list[dict], modulo: str):
    """Almacena preguntas en ChromaDB."""
    if not questions:
        return
    timestamp = int(time.time() * 1000)
    docs = []
    metas = []
    ids = []
    for i, q in enumerate(questions):
        docs.append(json.dumps(q, ensure_ascii=False))
        metas.append({
            "modulo": modulo,
            "tipo": "pregunta_generada",
            "competencia": "Específica",
            "programa": q.get("programa", ""),
            "tipo_ingles": "",
            "nivel_cefr": "",
            "nivel_dificultad": q.get("nivel_dificultad", "intermedio"),
            "modulo_especifico": q.get("modulo_especifico", ""),
        })
        ids.append(f"esp_pregen_{timestamp}_{i}")
    try:
        collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"    ✅ Almacenadas {len(questions)} preguntas en ChromaDB")
    except Exception as e:
        print(f"    ❌ Error guardando: {e}")


def _count_existing(collection, programa: str) -> int:
    try:
        res = collection.get(
            where={"$and": [
                {"competencia": "Específica"},
                {"programa": programa},
            ]},
            include=["metadatas"],
        )
        return len(res.get("metadatas", []))
    except Exception:
        return 0


def _get_modulo_slug(programa: str) -> str:
    """Map programa → ChromaDB modulo slug."""
    SLUGS = {
        "Administración de Empresas": "administracion-de-empresas",
        "Contaduría Pública": "contaduria-publica",
        "Licenciatura en Ciencias Sociales": "licenciatura-ciencias-sociales",
        "Ingeniería Electrónica": "ingenieria-electronica",
        "Ingeniería de Sistemas y Computación": "ingenieria-de-sistemas-y-computacion",
        "Ingeniería Agronómica": "ingenieria-agronomica",
        "Zootecnia": "zootecnia",
        "Licenciatura en Educación Física, Recreación y Deportes": "licenciatura-educacion-fisica",
    }
    return SLUGS.get(programa, programa.lower().replace(" ", "-"))


def generar_para_programa(programa: str, collection) -> int:
    existentes = _count_existing(collection, programa)
    print(f"\n{'='*60}")
    print(f"  {programa}")
    print(f"  Existentes en DB: {existentes}")

    if existentes >= MIN_TARGET:
        print(f"  ⚠️ Ya tiene {existentes}. Generando extra para basicas/avanzadas...")
        # No skip — we need to fill basic/advanced too

    modulos = get_modulos_for_programa(programa)
    if not modulos:
        print(f"  ⚠️ No tiene módulos configurados. Saltando.")
        return 0

    print(f"  Módulos: {', '.join(m['nombre'] for m in modulos)}")

    DIFFICULTIES = ["basico", "intermedio", "avanzado"]
    all_raw: list[dict] = []
    for mod_config in modulos:
        mod_nombre = mod_config["nombre"]
        mod_total = 0
        for batch_idx in range(NUM_BATCHES):
            try:
                diff = DIFFICULTIES[batch_idx % 3]
                print(f"    🔄 '{mod_nombre}' batch {batch_idx+1}/{NUM_BATCHES} [{diff}]...", end=" ", flush=True)
                result = _generate_batch(BATCH_SIZE, programa, mod_config, diff)
                print(f"→ {len(result)} preguntas", flush=True)
                all_raw.extend(result)
                mod_total += len(result)
            except Exception as e:
                print(f"→ ❌ Error: {e}")
                traceback.print_exc()
            time.sleep(1)
        print(f"    📦 '{mod_nombre}' total: {mod_total} preguntas crudas")

    if not all_raw:
        print(f"  🔍 0 preguntas crudas totales.")
        return existentes

    # Filtrar
    valid = _filter_and_build(all_raw, programa)
    print(f"  🔍 Tras filtros y dedup: {len(valid)} preguntas válidas")

    if valid:
        modulo = _get_modulo_slug(programa)
        _store_questions(collection, valid, modulo)

    return existentes + len(valid)


def main():
    print("=" * 60)
    print("  PRE-GENERACIÓN DE BANCO DE PREGUNTAS ESPECÍFICAS")
    print("  ICFES Pro AI — Universidad de Cundinamarca")
    print("=" * 60)

    ChromaService.initialize()
    collection = ChromaService.get_collection()

    resumen = {}
    for programa in PROGRAMA_MODULOS_ESPECIFICOS:
        total = generar_para_programa(programa, collection)
        resumen[programa] = total
        time.sleep(2)

    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    for programa, total in resumen.items():
        status = "✅" if total >= MIN_TARGET else "⚠️"
        print(f"  {status} {programa}: {total} preguntas")
    print("=" * 60)


if __name__ == "__main__":
    main()
