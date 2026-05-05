"""
Script de pre-generación LIMPIA de Razonamiento Cuantitativo.
Estrategia: batches pequeños (4 preguntas), temas rotativos, retry agresivo.
"""
import sys, os, json, time, random, re, traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.chroma_client import ChromaService
from app.services.gemini_client import get_gemini_quiz_model
from app.config.rc_config import RC_TOPICS, RC_ESTRUCTURA_ICFES

PROGRAMAS = [
    "Administracion de Empresas",
    "Contaduria Publica",
    "Ingenieria de Sistemas y Computacion",
    "Ingenieria Electronica",
    "Ingenieria Agronomica",
    "Zootecnia",
    "Licenciatura en Ciencias Sociales",
    "Licenciatura en Educacion Fisica, Recreacion y Deportes",
]

BATCH_SIZE = 4
BATCHES_PER_PROG = 8
MIN_TARGET = 30


def _safe_json_parse(text: str) -> list[dict] | None:
    """Intenta parsear JSON con múltiples estrategias de recuperación."""
    if not text:
        return None

    # Clean markdown fences
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.strip().startswith("json"):
            text = text.strip()[4:]
    text = text.strip()

    # Balanced bracket extraction
    start_idx = text.find("[")
    if start_idx != -1:
        depth = 0
        end_idx = -1
        for i in range(start_idx, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        if end_idx != -1:
            text = text[start_idx:end_idx + 1]

    # Attempt 1: direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # Attempt 2: repair control chars (literal newlines inside strings)
    try:
        repaired = _repair_ctrl_chars(text)
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # Attempt 3: repair LaTeX backslashes
    try:
        repaired = _repair_latex(text)
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # Attempt 4: combined control + LaTeX repair
    try:
        repaired = _repair_latex(_repair_ctrl_chars(text))
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # Attempt 5: unescape quotes
    try:
        unescaped = text.replace('\\"', '"')
        parsed = json.loads(unescaped)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return None


def _repair_ctrl_chars(raw: str) -> str:
    """Escapa saltos de línea y tabs dentro de strings JSON."""
    result = []
    i = 0
    in_string = False
    escape_next = False
    while i < len(raw):
        ch = raw[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
        if in_string and ch == "\n":
            result.append("\\n")
            i += 1
            continue
        if in_string and ch == "\r":
            result.append("\\r")
            i += 1
            continue
        if in_string and ch == "\t":
            result.append("\\t")
            i += 1
            continue
        result.append(ch)
        i += 1
    return "".join(result)


def _repair_latex(raw: str) -> str:
    """Escapa comandos LaTeX que rompen JSON (\f, \b, \t, etc.)."""
    text = raw
    cmds = [
        "frac", "binom", "sqrt", "times", "cdot", "Delta", "theta",
        "alpha", "beta", "gamma", "pi", "sigma", "lambda", "mu",
        "sum", "prod", "int", "infty", "partial", "nabla", "approx",
        "Rightarrow", "Leftrightarrow", "longrightarrow", "text",
        "textbf", "textit", "overline", "underline", "bar", "hat",
        "pm", "div", "neq", "leq", "geq", "equiv", "sim", "propto",
        "subseteq", "supseteq", "in", "notin", "forall", "exists",
        "cup", "cap", "emptyset", "angle", "triangle", "binom",
    ]
    for cmd in cmds:
        text = text.replace(f"\\{cmd}", f"\\\\{cmd}")
    return text


def _generate_rc_batch(cantidad: int, programa: str, dificultad: str) -> list[dict]:
    """Genera un batch pequeño de preguntas RC."""
    available = list(RC_TOPICS)
    random.shuffle(available)
    sample_topics = available[:6]
    temas_str = "\n".join(f"  - {t}" for t in sample_topics)

    model = get_gemini_quiz_model()

    prompt = (
        f"Eres un disenador experto del ICFES Saber Pro.\n"
        f"Genera exactamente {cantidad} preguntas de Razonamiento Cuantitativo.\n\n"
        f"Programa: {programa}\n"
        f"Dificultad: {dificultad}\n\n"
        f"Temas sugeridos:\n{temas_str}\n\n"
        f"REGLAS:\n"
        f"- 4 opciones (A,B,C,D). Una correcta.\n"
        f"- texto_base: caso numerico con tabla Markdown y datos concretos.\n"
        f"- Opciones: resultados numericos o interpretaciones cuantitativas.\n"
        f"- Explicacion: procedimiento paso a paso.\n"
        f"- LaTeX con DOBLE barra: $\\\\frac{{a}}{{b}}$, NO $\\frac$\n"
        f"- ESCAPA SIEMPRE: \\\\frac, \\\\Delta, \\\\times, \\\\binom, etc.\n"
        f"- No uses frases conversacionales (\"Aqui tienes\", \"Te presento\").\n"
        f"- Sin encabezados de pregunta.\n"
        f"- Devuelve SOLO el array JSON, sin markdown.\n"
        f"- Usa comillas simples si el texto lleva comillas.\n\n"
        f'Formato: [{{"texto_base":"...","enunciado":"...",'
        f'"opciones":["A. ...","B. ...","C. ...","D. ..."],'
        f'"respuesta_correcta":"A. ...","explicacion":"...",'
        f'"competencia":"Razonamiento Cuantitativo",'
        f'"nivel_dificultad":"{dificultad}"}}]'
    )

    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    parsed = _safe_json_parse(text)
    return parsed or []


def _filter_questions(raw: list[dict], programa: str) -> list[dict]:
    valid = []
    seen = set()
    for item in raw:
        try:
            opciones = item.get("opciones", [])
            if not isinstance(opciones, list) or len(opciones) < 4:
                continue
            clean_opts = []
            for j, opt in enumerate(opciones[:4]):
                opt = str(opt).strip()
                letter = chr(65 + j)
                if not re.match(r"^[A-Da-d]\.", opt):
                    opt = f"{letter}. {opt}"
                clean_opts.append(opt)

            texto_base = str(item.get("texto_base", "")).strip()
            if len(texto_base) < 40:
                continue

            enunciado = re.sub(r"[ \t]+", " ", str(item.get("enunciado", ""))).strip()
            if len(enunciado) < 28:
                continue

            key = enunciado.lower()[:80]
            if key in seen:
                continue
            seen.add(key)

            resp = str(item.get("respuesta_correcta", "")).strip()
            if resp not in clean_opts:
                nc = re.sub(r"^[A-Da-d]\.\s*", "", resp).strip().lower()
                m = next((o for o in clean_opts if nc and nc in re.sub(r"^[A-Da-d]\.\s*", "", o).strip().lower()), None)
                resp = m or clean_opts[0]

            valid.append({
                "texto_base": texto_base,
                "enunciado": enunciado,
                "opciones": clean_opts,
                "respuesta_correcta": resp,
                "explicacion": str(item.get("explicacion", "")),
                "competencia": "Razonamiento Cuantitativo",
                "programa": programa,
                "nivel_dificultad": str(item.get("nivel_dificultad", "intermedio")),
            })
        except Exception:
            continue
    return valid


def _store(collection, questions: list[dict]):
    if not questions:
        return
    ts = int(time.time() * 1000)
    docs, metas, ids = [], [], []
    for i, q in enumerate(questions):
        docs.append(json.dumps(q, ensure_ascii=False))
        metas.append({
            "modulo": "general",
            "tipo": "pregunta_generada",
            "competencia": "Razonamiento Cuantitativo",
            "programa": q.get("programa", ""),
            "tipo_ingles": "",
            "nivel_cefr": "",
            "nivel_dificultad": q.get("nivel_dificultad", "intermedio"),
            "modulo_especifico": "",
        })
        ids.append(f"rc_clean_{ts}_{i}")
    try:
        collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"    Almacenadas {len(questions)} preguntas RC")
    except Exception as e:
        print(f"    Error guardando: {e}")


def delete_old(collection):
    where = {"$and": [{"tipo": "pregunta_generada"}, {"competencia": "Razonamiento Cuantitativo"}]}
    try:
        existing = collection.get(where=where, include=["metadatas"])
        count = len(existing.get("ids", []))
        if count > 0:
            collection.delete(where=where)
            print(f"  Eliminadas {count} preguntas RC viejas")
        return count
    except Exception as e:
        print(f"  Error eliminando: {e}")
        return 0


def generar(programa: str, collection) -> int:
    print(f"\n{'='*50}")
    print(f"  RC - {programa}")

    all_raw = []
    diffs = ["intermedio", "basico", "intermedio", "avanzado"] * 3

    for bi in range(BATCHES_PER_PROG):
        diff = diffs[bi]
        for attempt in range(4):
            try:
                print(f"    Batch {bi+1}/{BATCHES_PER_PROG} [{diff}]", end=" ", flush=True)
                result = _generate_rc_batch(BATCH_SIZE, programa, diff)
                print(f"-> {len(result)}", flush=True)
                all_raw.extend(result)
                break
            except Exception as e:
                msg = str(e)[:150]
                if attempt < 3:
                    wait = (attempt + 1) * 4
                    print(f"-> retry {attempt+1} en {wait}s: {msg}", flush=True)
                    time.sleep(wait)
                else:
                    print(f"-> FALLO: {msg}", flush=True)
        time.sleep(1.5)

    if not all_raw:
        print(f"  0 preguntas crudas.")
        return 0

    valid = _filter_questions(all_raw, programa)
    print(f"  {len(all_raw)} crudas -> {len(valid)} validas")

    if valid:
        _store(collection, valid)
    return len(valid)


def main():
    print("=" * 50)
    print("  REGENERACION RC - RAZONAMIENTO CUANTITATIVO")
    print("=" * 50)

    ChromaService.initialize()
    coll = ChromaService.get_collection()
    print(f"\n  Docs iniciales: {coll.count()}")

    print("\n  PASO 1: Limpiando viejas...")
    delete_old(coll)

    print("\n  PASO 2: Generando banco limpio...")
    resumen = {}
    for prog in PROGRAMAS:
        total = generar(prog, coll)
        resumen[prog] = total
        time.sleep(2)

    print("\n" + "=" * 50)
    print("  RESUMEN FINAL")
    print("=" * 50)
    total_gen = 0
    for prog, tot in resumen.items():
        s = "OK" if tot >= MIN_TARGET else "--"
        print(f"  {s} {prog}: {tot}")
        total_gen += tot
    print(f"  TOTAL: {total_gen} | Docs finales: {coll.count()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
