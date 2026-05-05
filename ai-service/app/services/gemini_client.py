"""
Cliente Gemini Flash para generación de respuestas RAG.
RF-07: Envía contexto recuperado y genera respuesta con fuentes.
"""

import os
import asyncio
import base64
import json
import re
import time
import unicodedata
from typing import AsyncGenerator
import google.generativeai as genai
from functools import lru_cache

# Config para el chat RAG — tokens suficientes para simulacros y respuestas largas
GENERATION_CONFIG = {
    "max_output_tokens": 2500,
    "temperature": 0.3,
    "top_p": 0.75,
}

# Config para generación de preguntas de práctica — necesita más tokens para el JSON
GENERATION_CONFIG_QUIZ = {
    "max_output_tokens": 8192,
    "temperature": 0.25,
    "top_p": 0.75,
}


@lru_cache(maxsize=1)
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG)


def get_gemini_quiz_model():
    """Modelo con más tokens para generar preguntas de práctica en JSON."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG_QUIZ)


def get_gemini_image_model():
    """Modelo para generar guía visual en imagen."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")
    return genai.GenerativeModel(model_name)


def _candidate_image_models() -> list[str]:
    primary = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation").strip()
    candidates = [
        primary,
        "gemini-2.0-flash-preview-image-generation",
        "gemini-2.0-flash-exp-image-generation",
        "gemini-2.5-flash-image-preview",
        "imagen-3.0-generate-002",
    ]
    seen = set()
    unique: list[str] = []
    for name in candidates:
        if name and name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def _build_prompt(pregunta: str, contexto: list[dict], nombre: str = "", historial: list[dict] | None = None) -> str:
    """Construye el prompt RAG con personalización por estudiante."""
    nombre_corto = nombre.strip().split()[0].title() if nombre.strip() else "estudiante"

    ejemplos = [c for c in contexto if c.get("tipo") == "ejemplo"]
    practica  = [c for c in contexto if c.get("tipo") == "practica"]
    otros     = [c for c in contexto if c.get("tipo") not in ("ejemplo", "practica")]

    bloques = []
    if ejemplos:
        texto = "\n\n".join(f"[{i+1}] {c.get('fuente','ICFES')}\n{c['text']}" for i, c in enumerate(ejemplos))
        bloques.append(f"EJEMPLOS OFICIALES ICFES:\n{texto}")
    if practica:
        texto = "\n\n".join(f"[{i+1}] {c.get('fuente','ICFES')}\n{c['text']}" for i, c in enumerate(practica))
        bloques.append(f"FRAGMENTOS DEL CUADERNILLO:\n{texto}")
    if otros:
        texto = "\n\n".join(f"[{i+1}] {c.get('fuente','ICFES')}\n{c['text']}" for i, c in enumerate(otros))
        bloques.append(f"CONTEXTO:\n{texto}")

    hay_contexto = len(bloques) > 0
    ctx_bloque = ("\n\n".join(bloques) + "\n\n") if bloques else ""

    if hay_contexto:
        instruccion_contexto = (
            "- Si es una pregunta académica: explica apoyándote en el contexto oficial y SIEMPRE cierra con UNA pregunta\n"
            "  de verificación de comprensión (no una pregunta de cortesía).\n"
        )
    else:
        instruccion_contexto = (
            "- No tengo fragmentos específicos en este momento, pero tienes conocimiento profundo sobre Saber Pro.\n"
            "- Responde con contenido CONCRETO sobre el tema usando tu conocimiento general de Saber Pro.\n"
            "- NO preguntes qué quiere practicar si el mensaje ya especifica un tema — ¡ya te lo dijo!\n"
            "- Explica de forma guiada el tema pedido y cierra con una pregunta de verificación o profundización.\n"
        )

    historial = historial or []
    historial_reciente = historial[-6:]
    historial_bloque = "\n".join(
        f"- {h.get('role', 'user')}: {h.get('content', '').strip()}"
        for h in historial_reciente
        if str(h.get('content', '')).strip()
    )

    return (
        f"Eres Saber Pro AI, el tutor personal de {nombre_corto} en la Universidad de Cundinamarca.\n"
        f"Acompañas a {nombre_corto} en su preparación para Saber Pro con cercanía, energía positiva y tono colombiano natural.\n\n"
        "CÓMO RESPONDER:\n"
        f"- Llama a {nombre_corto} por su nombre de forma natural (una sola vez, al inicio o al cierre).\n"
        "- Tutea siempre al usuario (usa 'tu' y 'te'), evita tratarlo de 'usted'.\n"
        "- Usa lenguaje colombiano cercano, pero muy sutil: maximo 1 expresion coloquial corta por respuesta.\n"
        "- Evita exceso de dichos o muletillas; prioriza claridad academica.\n"
        "- Incluye un toque de humor cercano cuando encaje (maximo 1 chiste corto o comparacion divertida).\n"
        "- Mantén el respeto: nada ofensivo, nada pesado y evita sonar forzado o caricaturesco.\n"
        "- Entrega entre 4 y 8 oraciones utiles en total. Evita respuestas de 1-2 oraciones.\n"
        "- Directo al grano, pero con suficiente desarrollo para enseñar, no solo saludar.\n"
        "- Enfoca la respuesta como aprendizaje guiado: explica + verifica comprensión.\n"
        "- Si el mensaje no es academico/Saber Pro, reconoce breve y redirige al estudio sin inventar analogias raras.\n"
        "- Si el mensaje del estudiante parece una RESPUESTA (por ejemplo no trae '?'), evalúa si va bien, corrige con tacto y explica el porqué.\n"
        "- Cierra OBLIGATORIAMENTE con UNA sola pregunta corta de chequeo para validar comprensión (no más de una).\n"
        "- Alterna nivel de dificultad (fácil/medio) según lo que el estudiante muestre en sus respuestas.\n"
        "- Si es un saludo o mensaje corto SIN tema específico: responde brevemente y PREGUNTA qué quiere repasar.\n"
        f"{instruccion_contexto}"
        "- Sin encabezados '### Título'. Sin listas largas. **Negrita** solo para máximo 2 términos clave.\n\n"
        "FORMATO OBLIGATORIO:\n"
        "1) Explicación guiada corta del punto clave.\n"
        "2) Micro retroalimentación (qué va bien / qué ajustar).\n"
        "3) Pregunta final de chequeo (exactamente 1).\n\n"
        "HISTORIAL RECIENTE DEL CHAT (usa esto para continuidad y retroalimentación):\n"
        f"{historial_bloque if historial_bloque else '- Sin historial previo'}\n\n"
        f"{ctx_bloque}"
        f"MENSAJE DE {nombre_corto.upper()}: {pregunta}\n\nRESPUESTA:"
    )


def _extract_text(response) -> str:
    """Extrae texto de Gemini de forma robusta (incluye candidatos multipart)."""
    try:
        candidates = getattr(response, "candidates", None) or []
        parts_text: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    parts_text.append(text)
        if parts_text:
            return "".join(parts_text).strip()
    except Exception:
        pass

    try:
        return (getattr(response, "text", "") or "").strip()
    except Exception:
        return ""


def _looks_truncated(text: str) -> bool:
    t = text.strip()
    if len(t) < 40:
        return False
    return not t.endswith((".", "?", "!", "…"))


async def get_ai_response(prompt: str, model_name: str = "gemini-2.5-flash", max_output_tokens: int = 3000, temperature: float = 0.7) -> str:
    """Genera una respuesta directa con Gemini (sin pipeline RAG). Usado por mutador y generación."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name, generation_config={
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
    })
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, model.generate_content, prompt)
    return _extract_text(response)


def _generate_sync(prompt: str) -> str:
    """Wrapper síncrono de Gemini para usar en thread pool."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    text = _extract_text(response)

    # Si Gemini corta la salida a mitad de frase, pide continuación controlada.
    for _ in range(2):
        if not _looks_truncated(text):
            break

        continuation_prompt = (
            "Continua EXACTAMENTE desde donde quedó este borrador, sin repetir lo anterior.\n"
            "Debes cerrar la idea completa y terminar con una sola pregunta corta de verificación.\n\n"
            f"BORRADOR:\n{text}\n\nCONTINUACION:"
        )
        more_resp = model.generate_content(continuation_prompt)
        more = _extract_text(more_resp)
        if not more:
            break

        text = f"{text.rstrip()} {more.lstrip()}".strip()

    return text


async def generate_response(pregunta: str, contexto: list[dict], nombre: str = "", historial: list[dict] | None = None) -> dict:
    """Genera respuesta RAG con Gemini en thread pool (no bloquea event loop)."""
    fuentes = list(set(c.get("fuente", "Guía ICFES") for c in contexto if c.get("fuente")))
    prompt = _build_prompt(pregunta, contexto, nombre, historial)

    loop = asyncio.get_event_loop()
    texto = await loop.run_in_executor(None, _generate_sync, prompt)

    return {"respuesta": texto, "fuentes": fuentes}


async def generate_response_stream(
    pregunta: str, contexto: list[dict], nombre: str = "", historial: list[dict] | None = None
) -> AsyncGenerator[str, None]:
    """Streaming estable: genera respuesta completa y la envía por fragmentos para evitar cortes."""
    prompt = _build_prompt(pregunta, contexto, nombre, historial)
    try:
        loop = asyncio.get_running_loop()
        texto_completo = await loop.run_in_executor(None, _generate_sync, prompt)

        chunk_size = 140
        for i in range(0, len(texto_completo), chunk_size):
            yield texto_completo[i:i + chunk_size]
            await asyncio.sleep(0)
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "quota" in err_msg.lower():
            yield "\n\n*Hoy se alcanzó el límite de uso del modelo. Intenta más tarde.*"
        else:
            yield "\n\n*No pude obtener respuesta completa en este momento. Intenta de nuevo.*"


def _build_visual_prompt(programa: str, pregunta: str, respuesta: str) -> str:
    resumen = respuesta[:1200]
    return (
        "Crea una imagen educativa tipo infografia limpia para estudiantes universitarios. "
        "Debe verse moderna, clara y motivante, con paleta azul/verde suave y elementos visuales de estudio. "
        "Incluye maximo 3 bloques visuales conceptuales (sin parrafos largos ni texto pequeño). "
        "Evita logos, marcas de agua y contenido no academico.\n\n"
        f"Programa: {programa}\n"
        f"Pregunta del estudiante: {pregunta}\n"
        f"Resumen de la explicacion: {resumen}\n\n"
        "Objetivo: servir como guia visual rapida para repasar este tema de Saber Pro."
    )


def _extract_image_data_url(response) -> str | None:
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if not inline_data:
                    continue

                mime_type = getattr(inline_data, "mime_type", None) or "image/png"
                data = getattr(inline_data, "data", None)
                if not data:
                    continue

                if isinstance(data, bytes):
                    b64 = base64.b64encode(data).decode("ascii")
                else:
                    # El SDK puede devolver base64 ya codificado como str.
                    b64 = str(data)
                return f"data:{mime_type};base64,{b64}"
    except Exception:
        return None
    return None


async def generate_guide_image(pregunta: str, respuesta: str, programa: str) -> dict | None:
    """Genera una imagen guía basada en la respuesta del tutor."""
    prompt = _build_visual_prompt(programa=programa, pregunta=pregunta, respuesta=respuesta)
    loop = asyncio.get_running_loop()

    errors: list[str] = []

    for model_name in _candidate_image_models():
        def _run():
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt)

        try:
            resp = await loop.run_in_executor(None, _run)
            image_data_url = _extract_image_data_url(resp)
            if not image_data_url:
                errors.append(f"{model_name}: sin imagen en la respuesta")
                continue
            return {
                "image_data_url": image_data_url,
                "caption": "Guia visual del tema",
                "model_used": model_name,
            }
        except Exception as e:
            errors.append(f"{model_name}: {str(e)[:120]}")

    return {
        "image_data_url": None,
        "caption": None,
        "model_used": None,
        "error": " | ".join(errors[:3]) if errors else "No se pudo generar imagen",
    }


def _parse_json_relaxed(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        # Fallback: modelos a veces devuelven JSON escapado dentro de string.
        try:
            unescaped = (
                raw[start:end + 1]
                .replace('\\"', '"')
                .replace('\\n', ' ')
                .replace('\\{', '{')
                .replace('\\}', '}')
                .replace('\\[', '[')
                .replace('\\]', ']')
            )
            return json.loads(unescaped)
        except Exception:
            return None


async def generate_visual_aids(pregunta: str, respuesta: str, programa: str) -> dict:
    """Genera apoyo visual textual: fórmula LaTeX + pasos de guía visual."""
    prompt = (
        "Analiza la explicación y devuelve SOLO JSON con esta estructura exacta:\n"
        "{\n"
        "  \"latex_formula\": \"string o vacio\",\n"
        "  \"latex_explanation\": \"string corto\",\n"
        "  \"guide_steps\": [\"paso 1\", \"paso 2\", \"paso 3\"],\n"
        "  \"guide_title\": \"titulo corto\"\n"
        "}\n\n"
        "Reglas:\n"
        "- Si aplica matematica/calculo/porcentajes/proporciones, incluye una formula en LaTeX valida.\n"
        "- Si NO aplica formula, latex_formula debe ser vacio.\n"
        "- guide_steps: entre 3 y 5 pasos maximo, concretos y visuales.\n"
        "- No incluyas markdown ni texto fuera del JSON.\n\n"
        f"Programa: {programa}\n"
        f"Pregunta: {pregunta}\n"
        f"Respuesta: {respuesta[:2500]}"
    )

    loop = asyncio.get_running_loop()

    def _run():
        model = get_gemini_model()
        return model.generate_content(prompt)

    try:
        resp = await loop.run_in_executor(None, _run)
        text = _extract_text(resp)
        data = _parse_json_relaxed(text) or {}
        steps = data.get("guide_steps") if isinstance(data.get("guide_steps"), list) else []
        clean_steps = [str(s).strip() for s in steps if str(s).strip()][:5]
        return {
            "latex_formula": str(data.get("latex_formula") or "").strip(),
            "latex_explanation": str(data.get("latex_explanation") or "").strip(),
            "guide_title": str(data.get("guide_title") or "Guia visual paso a paso").strip(),
            "guide_steps": clean_steps,
        }
    except Exception:
        return {
            "latex_formula": "",
            "latex_explanation": "",
            "guide_title": "Guia visual paso a paso",
            "guide_steps": [],
        }


def _parse_json_array_relaxed(text: str) -> list[str] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start:end + 1])
        if isinstance(data, list):
            cleaned = []
            seen = set()
            for item in data:
                s = str(item).strip()
                key = s.lower()
                if s and key not in seen:
                    seen.add(key)
                    cleaned.append(s)
            return cleaned
        return None
    except Exception:
        return None


async def generate_fun_facts(programa: str, competencia: str, cantidad: int = 8) -> list[str]:
    """Genera datos curiosos breves, variados y no repetidos para la carga de practica."""
    prompt = (
        "Genera datos curiosos academicos para estudiantes que preparan Saber Pro.\n"
        f"Programa: {programa}\n"
        f"Competencia: {competencia}\n"
        f"Cantidad: {cantidad}\n\n"
        "Reglas estrictas:\n"
        "- Devuelve SOLO un array JSON de strings.\n"
        "- Cada dato debe ser breve (max 20 palabras).\n"
        "- Deben ser distintos entre si, sin repetir ideas.\n"
        "- Tono motivador, claro y academico.\n"
        "- No uses markdown ni texto fuera del JSON.\n"
    )

    loop = asyncio.get_running_loop()

    def _run():
        model = get_gemini_model()
        return model.generate_content(prompt)

    try:
        resp = await loop.run_in_executor(None, _run)
        text = _extract_text(resp)
        parsed = _parse_json_array_relaxed(text) or []
        return parsed[:cantidad]
    except Exception:
        return []


async def generate_practice_support(
    programa: str,
    competencia: str,
    enunciado: str,
    texto_base: str = "",
    opciones: list[str] | None = None,
    explicacion: str = "",
) -> dict:
    """Genera apoyo para practica: traduccion al espanol y visual cuando haga falta."""
    opciones = opciones or []
    opciones_json = json.dumps(opciones, ensure_ascii=False)

    prompt = (
        "Analiza una pregunta de practica y devuelve SOLO JSON valido con esta estructura exacta:\n"
        "{\n"
        "  \"mostrar_traduccion\": true/false,\n"
        "  \"texto_base_es\": \"...\",\n"
        "  \"enunciado_es\": \"...\",\n"
        "  \"opciones_es\": [\"...\", \"...\"],\n"
        "  \"explicacion_es\": \"...\",\n"
        "  \"requiere_visual\": true/false,\n"
        "  \"visual_descripcion\": \"...\"\n"
        "}\n\n"
        "Reglas estrictas:\n"
        "- Si la pregunta esta en ingles o la competencia es Ingles, mostrar_traduccion=true y traduce fielmente.\n"
        "- Si ya esta en espanol, mostrar_traduccion=false y deja campos de traduccion vacios.\n"
        "- Si el enunciado o texto base menciona grafica, graph, chart, tabla, figure o diagrama, requiere_visual=true.\n"
        "- visual_descripcion debe indicar en 1-2 frases que grafica mostrar para responder.\n"
        "- opciones_es debe conservar el sentido de cada opcion y mantener la misma cantidad.\n"
        "- Si mostrar_traduccion=true, traduce tambien la explicacion en explicacion_es.\n"
        "- Sin markdown ni texto extra fuera del JSON.\n\n"
        f"Programa: {programa}\n"
        f"Competencia: {competencia}\n"
        f"Texto base: {texto_base[:1800]}\n"
        f"Enunciado: {enunciado[:1200]}\n"
        f"Opciones: {opciones_json}\n"
        f"Explicacion: {explicacion[:1200]}\n"
    )

    loop = asyncio.get_running_loop()

    def _run():
        model = get_gemini_model()
        return model.generate_content(prompt)

    support = {
        "mostrar_traduccion": False,
        "texto_base_es": "",
        "enunciado_es": "",
        "opciones_es": [],
        "explicacion_es": "",
        "requiere_visual": False,
        "visual_descripcion": "",
        "image_data_url": None,
        "caption": None,
        "image_model_used": None,
    }

    try:
        resp = await loop.run_in_executor(None, _run)
        text = _extract_text(resp)
        data = _parse_json_relaxed(text) or {}

        support["mostrar_traduccion"] = bool(data.get("mostrar_traduccion", False))
        support["texto_base_es"] = str(data.get("texto_base_es") or "").strip()
        support["enunciado_es"] = str(data.get("enunciado_es") or "").strip()
        support["explicacion_es"] = str(data.get("explicacion_es") or "").strip()
        
        # Auto-wrap LaTeX in explicacion if missing $ delimiters
        expl_es = support["explicacion_es"]
        if expl_es and '$' not in expl_es:
            import re as _re
            expl_es = _re.sub(r'(\\approx|\\times|\\div|\\frac\{[^}]+\}\{[^}]+\}|\\sqrt\{[^}]+\}|\\pm|\\cdot|\\leq|\\geq|\\Delta|\\sum|\\int)', r'$\1$', expl_es)
            support["explicacion_es"] = expl_es
        support["requiere_visual"] = bool(data.get("requiere_visual", False))
        support["visual_descripcion"] = str(data.get("visual_descripcion") or "").strip()

        opciones_es = data.get("opciones_es") if isinstance(data.get("opciones_es"), list) else []
        clean_opciones_es = [str(o).strip() for o in opciones_es if str(o).strip()]
        if len(clean_opciones_es) == len(opciones):
            support["opciones_es"] = clean_opciones_es

        if support["requiere_visual"]:
            visual_context = (
                f"Texto base: {texto_base}\n"
                f"Enunciado: {enunciado}\n"
                f"Indicacion visual: {support['visual_descripcion']}"
            )
            image_result = await generate_guide_image(
                pregunta=enunciado,
                respuesta=visual_context,
                programa=programa,
            )
            if image_result:
                support["image_data_url"] = image_result.get("image_data_url")
                support["caption"] = image_result.get("caption") or "Grafica de apoyo para resolver la pregunta"
                support["image_model_used"] = image_result.get("model_used")
    except Exception:
        pass

    return support


async def generate_admin_analytics_response(task: str, analytics_context: dict) -> dict:
    """Genera analisis ejecutivo para coordinador con contexto de dashboard."""
    context_json = json.dumps(analytics_context or {}, ensure_ascii=False)

    loop = asyncio.get_running_loop()

    def _to_ascii(s: str) -> str:
        normalized = unicodedata.normalize("NFD", s)
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    def _latex_escape_text(s: str) -> str:
        text = _to_ascii(str(s or "").strip())
        text = text.replace("\\", "\\textbackslash{}")
        replacements = {
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _normalize_points(value) -> list[str]:
        if isinstance(value, list):
            raw_items = [str(v).strip() for v in value if str(v).strip()]
        elif isinstance(value, str):
            # Si viene una lista serializada, intentar parsearla primero.
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed_list = json.loads(stripped)
                    if isinstance(parsed_list, list):
                        raw_items = [str(v).strip() for v in parsed_list if str(v).strip()]
                    else:
                        raw_items = [stripped]
                except Exception:
                    raw_items = [stripped]
            else:
                # Mantener robustez del mensaje: priorizar bloque completo en lugar de fragmentarlo por punto.
                raw_items = [stripped]
        else:
            raw_items = []
        cleaned = [re.sub(r"\s+", " ", v).strip() for v in raw_items if re.sub(r"\s+", " ", v).strip()]
        return cleaned[:3]

    def _extract_nested_payload(value) -> dict | None:
        candidates: list[str] = []
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, list):
            candidates.extend(str(v) for v in value)

        for candidate in candidates:
            t = str(candidate or "").strip()
            if not t:
                continue
            parsed = _parse_json_relaxed(t)
            if parsed and any(k in parsed for k in ("resumen", "alertas", "acciones")):
                return parsed

            # Caso con llaves/quotes escapadas por respuesta previa.
            unescaped = t.replace("\\{", "{").replace("\\}", "}").replace('\\"', '"')
            parsed_unescaped = _parse_json_relaxed(unescaped)
            if parsed_unescaped and any(k in parsed_unescaped for k in ("resumen", "alertas", "acciones")):
                return parsed_unescaped

        return None

    def _build_section(title: str, items: list[str], add_break_after: bool = True) -> list[str]:
        safe_title = _latex_escape_text(title)
        safe_items = items or ["Sin datos disponibles"]
        lines = [f"\\text{{{safe_title}}} & \\text{{{safe_items[0]}}}\\\\"]
        for item in safe_items[1:]:
            lines.append(f"& \\text{{{item}}}\\\\")
        if not add_break_after and lines:
            lines[-1] = lines[-1][:-2]
        return lines

    def _is_contaminated_item(s: str) -> bool:
        t = str(s or "").lower()
        keys_count = sum(1 for key in ("resumen", "alertas", "acciones") if re.search(rf"\\b{key}\\b", t))
        has_json_shape = ("{" in t or "\\{" in t) and ("[" in t or "\\[" in t or ":" in t)
        has_section_pattern = (
            '"resumen"' in t or '\\"resumen\\"' in t or
            '"alertas"' in t or '\\"alertas\\"' in t or
            '"acciones"' in t or '\\"acciones\\"' in t
        )
        return has_json_shape and (keys_count >= 2 or has_section_pattern)

    def _clean_contaminated_items(items: list[str], section: str | None = None) -> list[str]:
        cleaned: list[str] = []
        for item in items:
            text_item = str(item or "").strip()
            if not text_item:
                continue

            if _is_contaminated_item(text_item):
                nested = _parse_json_relaxed(text_item)
                if not nested:
                    nested = _parse_json_relaxed(
                        text_item
                        .replace('\\{', '{')
                        .replace('\\}', '}')
                        .replace('\\[', '[')
                        .replace('\\]', ']')
                        .replace('\\"', '"')
                    )
                if nested and any(k in nested for k in ("resumen", "alertas", "acciones")):
                    nested_items = nested.get(section) if section else None
                    if isinstance(nested_items, list):
                        for nested_item in nested_items:
                            candidate = str(nested_item or "").strip()
                            if candidate:
                                cleaned.append(candidate)
                    continue

                # Fallback: intentar extraer frases entre comillas y descartar claves.
                quoted = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text_item)
                for q in quoted:
                    candidate = q.strip()
                    if candidate.lower() in ("resumen", "alertas", "acciones"):
                        continue
                    if len(candidate) > 8:
                        cleaned.append(candidate)

                # Ultimo recurso: si viene JSON truncado de una seccion, extraer cuerpo textual util.
                if section and not cleaned:
                    unescaped_item = text_item.replace('\\"', '"')
                    section_pattern = rf'^\s*\{{\s*"?{section}"?\s*:\s*\[\s*"?'
                    candidate = re.sub(section_pattern, "", unescaped_item, flags=re.IGNORECASE)
                    candidate = re.sub(r'"?\s*\]\s*\}?\s*$', "", candidate)
                    candidate = re.sub(r"\s+", " ", candidate).strip(" \"')]}\\")
                    if len(candidate) > 20:
                        cleaned.append(candidate)
                continue

            cleaned.append(text_item)

        return cleaned

    def _fmt_number(value: float | int | None, decimals: int = 1) -> str:
        if value is None:
            return "s/d"
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return "s/d"

    def _fmt_percent(value: float | int | None) -> str:
        if value is None:
            return "s/d"
        try:
            v = float(value)
            if 0 <= v <= 1:
                v *= 100
            return f"{v:.1f}%"
        except Exception:
            return "s/d"

    def _find_numeric(obj, key_candidates: list[str]) -> float | None:
        normalized_candidates = {k.lower() for k in key_candidates}

        def _walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if str(k).strip().lower() in normalized_candidates and isinstance(v, (int, float)):
                        return float(v)
                for v in node.values():
                    found = _walk(v)
                    if found is not None:
                        return found
            elif isinstance(node, list):
                for item in node:
                    found = _walk(item)
                    if found is not None:
                        return found
            return None

        return _walk(obj)

    def _worst_grade_block(ctx: dict) -> tuple[str | None, float | None, float | None]:
        grade_rows = None
        for key in ("por_grado", "grados", "detalle_grado", "grade_breakdown"):
            value = ctx.get(key)
            if isinstance(value, list) and value:
                grade_rows = value
                break
        if not grade_rows:
            return (None, None, None)

        best_row = None
        best_score = None
        for row in grade_rows:
            if not isinstance(row, dict):
                continue
            promedio = row.get("promedio")
            riesgo = row.get("riesgo")
            if not isinstance(promedio, (int, float)) and not isinstance(riesgo, (int, float)):
                continue
            p = float(promedio) if isinstance(promedio, (int, float)) else 65.0
            r = float(riesgo) if isinstance(riesgo, (int, float)) else 0.12
            if 0 <= r <= 1:
                r = r * 100
            score = (70 - p) + (r * 0.5)
            if best_score is None or score > best_score:
                best_score = score
                best_row = row

        if not best_row:
            return (None, None, None)

        grado = str(best_row.get("grado") or best_row.get("nivel") or "grupo critico")
        promedio = best_row.get("promedio") if isinstance(best_row.get("promedio"), (int, float)) else None
        riesgo = best_row.get("riesgo") if isinstance(best_row.get("riesgo"), (int, float)) else None
        return (grado, float(promedio) if promedio is not None else None, float(riesgo) if riesgo is not None else None)

    def _get_first_list(ctx: dict, keys: list[str]) -> list[dict]:
        for key in keys:
            value = ctx.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _extract_topic_metric(ctx: dict, topic_name_candidates: list[str]) -> float | None:
        topic_rows = _get_first_list(ctx, ["temas_top", "temas", "topics", "topicos"])
        if not topic_rows:
            return None

        candidates = [c.lower() for c in topic_name_candidates]
        for row in topic_rows:
            competencia = str(row.get("competencia") or row.get("tema") or row.get("name") or "").lower()
            if not competencia:
                continue
            if any(c in competencia for c in candidates):
                total = row.get("total")
                if isinstance(total, (int, float)):
                    return float(total)
        return None

    def _trend_delta_percent(ctx: dict) -> float | None:
        trend_rows = _get_first_list(ctx, ["tendencia", "trend", "serie_tiempo"])
        if len(trend_rows) < 2:
            return None
        first = trend_rows[0].get("total")
        last = trend_rows[-1].get("total")
        if not isinstance(first, (int, float)) or not isinstance(last, (int, float)):
            return None
        first_value = float(first)
        last_value = float(last)
        if abs(first_value) < 1e-9:
            return None
        return ((last_value - first_value) / first_value) * 100.0

    def _top_program(ctx: dict) -> tuple[str | None, float | None]:
        program_rows = _get_first_list(ctx, ["programas", "por_programa", "programas_top", "program_breakdown"])
        if not program_rows:
            return (None, None)

        best_name = None
        best_total = None
        for row in program_rows:
            total = row.get("total")
            if not isinstance(total, (int, float)):
                continue
            if best_total is None or float(total) > best_total:
                best_total = float(total)
                best_name = str(row.get("programa") or row.get("nombre") or row.get("label") or "Programa principal").strip() or "Programa principal"

        return (best_name, best_total)

    def _build_rule_based_admin_blocks(ctx: dict, task_text: str) -> tuple[list[str], list[str], list[str]]:
        promedio_global = _find_numeric(ctx, ["promedio_global", "promedio", "score_global", "promediopositivas", "promedio_positivas"])
        riesgo_alto = _find_numeric(ctx, ["riesgo_alto", "riesgo", "riesgo_critico", "at_risk_rate"])
        inasistencia = _find_numeric(ctx, ["inasistencia_media", "inasistencia", "ausentismo", "absentismo"])
        lectura = _find_numeric(ctx, ["lectura", "lectura_critica", "critical_reading"])
        cuantitativo = _find_numeric(ctx, ["cuantitativo", "razonamiento_cuantitativo", "matematicas", "quantitative"])

        total_consultas = _find_numeric(ctx, ["total_consultas", "totalconsultas", "consultas_totales"])
        estudiantes_unicos = _find_numeric(ctx, ["estudiantes_unicos", "estudiantesunicos", "usuarios_unicos"])
        consultas_hoy = _find_numeric(ctx, ["consultas_hoy", "consultashoy", "today_queries"])
        total_estudiantes = _find_numeric(ctx, ["total_estudiantes", "totalestudiantes", "students_total"])

        if lectura is None:
            lectura = _extract_topic_metric(ctx, ["lectura", "lectura critica"])
        if cuantitativo is None:
            cuantitativo = _extract_topic_metric(ctx, ["cuantitativo", "razonamiento", "matematica"])

        trend_delta = _trend_delta_percent(ctx)
        top_program_name, top_program_total = _top_program(ctx)
        grado_critico, promedio_grado, riesgo_grado = _worst_grade_block(ctx if isinstance(ctx, dict) else {})

        resumen: list[str] = []
        alertas: list[str] = []
        acciones: list[str] = []

        if total_consultas is not None and estudiantes_unicos is not None:
            resumen.append(
                f"El uso del asistente registra {_fmt_number(total_consultas, 0)} consultas sobre {_fmt_number(estudiantes_unicos, 0)} estudiantes unicos; esta intensidad valida adopcion, pero exige priorizar seguimiento por programa para convertir interaccion en mejora medible de desempeno."
            )
        else:
            resumen.append(
                f"El promedio global ({_fmt_number(promedio_global)}) junto con riesgo alto ({_fmt_percent(riesgo_alto)}) sugiere presion sobre resultados institucionales; conviene focalizar seguimiento en cohortes con menor rendimiento para estabilizar indicadores antes del siguiente corte academico."
            )

        if lectura is not None or cuantitativo is not None:
            resumen.append(
                f"La brecha entre lectura critica ({_fmt_number(lectura)}) y razonamiento cuantitativo ({_fmt_number(cuantitativo)}) muestra desalineacion curricular; priorizar ajustes por competencia mejoraria consistencia del desempeno y reduciria dispersion entre programas en evaluaciones externas."
            )
        elif trend_delta is not None:
            trend_direction = "al alza" if trend_delta >= 0 else "a la baja"
            resumen.append(
                f"La tendencia reciente de consultas viene {trend_direction} ({_fmt_number(trend_delta)}% en la ventana analizada), senal de cambio en demanda academica; conviene ajustar capacidad de respuesta docente para sostener oportunidad y calidad del acompanamiento."
            )
        else:
            resumen.append(
                "No se identificaron metricas por competencia en el contexto cargado; esto limita priorizacion fina. Es clave consolidar tablero por modulo para definir intervenciones diferenciadas y evitar decisiones generales con bajo impacto real."
            )

        focus = re.sub(r"\s+", " ", str(task_text or "")).strip()
        if focus:
            resumen.append(
                f"El enfoque solicitado ({focus[:120]}) es viable si se traduce en metas semanales por programa, responsables definidos y trazabilidad de avance; sin ese cierre operativo, la mejora tendera a diluirse en acciones aisladas."
            )

        if grado_critico:
            alertas.append(
                f"{grado_critico} concentra la mayor criticidad con promedio {_fmt_number(promedio_grado)} y riesgo {_fmt_percent(riesgo_grado)}; mantener la misma intensidad de acompanamiento puede ampliar la brecha interna y afectar comparabilidad institucional en el siguiente reporte." 
            )
        elif top_program_name and top_program_total is not None:
            alertas.append(
                f"{top_program_name} concentra {_fmt_number(top_program_total, 0)} interacciones, lo que puede ocultar baja participacion de otros programas; sin estrategia de cobertura diferencial, la adopcion seguira sesgada y reducira equidad del impacto institucional."
            )

        if inasistencia is not None:
            alertas.append(
                f"La inasistencia media ({_fmt_percent(inasistencia)}) compromete continuidad de aprendizaje y sesga resultados de seguimiento; sin control temprano de asistencia y recuperacion academica, la probabilidad de rezago seguira creciendo en grupos vulnerables."
            )
        elif consultas_hoy is not None and total_consultas is not None:
            peso_hoy = (float(consultas_hoy) / float(total_consultas) * 100.0) if float(total_consultas) > 0 else 0.0
            alertas.append(
                f"Las consultas de hoy representan {_fmt_number(peso_hoy)}% del acumulado ({_fmt_number(consultas_hoy, 0)} de {_fmt_number(total_consultas, 0)}), indicador sensible a picos operativos; sin monitoreo diario por franja, puede degradarse la experiencia de respuesta en momentos criticos."
            )
        else:
            alertas.append(
                "No hay trazabilidad consolidada de inasistencia en el contexto actual; esta brecha impide explicar variaciones de desempeno y puede conducir a intervenciones incompletas frente a factores de permanencia estudiantil."
            )

        missing_metrics = []
        if promedio_global is None:
            missing_metrics.append("promedio global")
        if riesgo_alto is None:
            missing_metrics.append("riesgo alto")
        if lectura is None and cuantitativo is None:
            missing_metrics.append("competencias clave")
        if missing_metrics:
            alertas.append(
                f"Faltan metricas criticas ({', '.join(missing_metrics)}), lo que reduce confiabilidad del briefing; antes de escalar decisiones, valida integridad del pipeline analitico para evitar priorizaciones con evidencia incompleta."
            )

        if total_estudiantes is not None and estudiantes_unicos is not None and float(total_estudiantes) > 0:
            cobertura = float(estudiantes_unicos) / float(total_estudiantes) * 100.0
            acciones.append(
                f"Lanza en 7 dias una campana de cobertura para elevar uso desde {_fmt_number(cobertura)}% de la base estudiantil ({_fmt_number(estudiantes_unicos, 0)}/{_fmt_number(total_estudiantes, 0)}), con metas por programa y seguimiento diario de conversion."
            )

        acciones.append(
            "En 7 dias, activa celda de seguimiento con coordinacion, analitica y lideres de programa: define semaforo por cohorte, meta semanal de mejora y responsable por accion, con corte de control cada 48 horas."
        )
        acciones.append(
            "Implementa microintervenciones por competencia en cursos con menor desempeno: dos sesiones focalizadas, banco de reactivos por nivel y retroalimentacion docente estandarizada, midiendo variacion de avance al cierre de la semana."
        )
        acciones.append(
            "Publica tablero ejecutivo minimo con tres KPI (promedio, riesgo, asistencia), comparativo por programa y alerta automatica de deterioro; sin visibilidad diaria, la toma de decisiones seguira reactiva y tardia."
        )

        return (resumen[:3], alertas[:3], acciones[:3])

    def _build_grounded_admin_blocks(ctx: dict, task_text: str) -> tuple[list[str], list[str], list[str]]:
        metricas = ctx.get("metricas") if isinstance(ctx.get("metricas"), dict) else {}

        def _parse_rate_like(value) -> float | None:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                normalized = value.replace("%", "").replace(",", ".").strip()
                try:
                    parsed = float(normalized)
                    return parsed
                except Exception:
                    return None
            return None

        total_consultas = _find_numeric(metricas, ["totalConsultas", "total_consultas", "consultas_totales"])
        estudiantes_unicos = _find_numeric(metricas, ["estudiantesUnicos", "estudiantes_unicos", "usuarios_unicos"])
        consultas_hoy = _find_numeric(metricas, ["consultasHoy", "consultas_hoy", "today_queries"])
        total_estudiantes = _find_numeric(metricas, ["totalEstudiantes", "total_estudiantes"])
        promedio_positivas = None
        for key in ("promedioPositivas", "promedio_positivas"):
            if key in metricas:
                promedio_positivas = _parse_rate_like(metricas.get(key))
                if promedio_positivas is not None:
                    break

        filtros = ctx.get("filtros") if isinstance(ctx.get("filtros"), dict) else {}
        filtro_programa = str(filtros.get("programa") or "").strip()
        filtro_es_global = filtro_programa.lower() in ("", "todos", "todos los programas", "sin filtro")

        program_rows = _get_first_list(ctx, ["programas", "por_programa", "programas_top"])
        trend_rows = _get_first_list(ctx, ["tendencia", "trend", "serie_tiempo"])
        topic_rows = _get_first_list(ctx, ["temas_top", "temas", "topics"])
        practice_rows = _get_first_list(ctx, ["resultados_practicas", "practicas_resultados", "practice_results", "entrenamientos", "training_results"])
        training_avg = _find_numeric(ctx, ["promedio_practicas", "practice_avg", "promedio_entrenamiento", "training_avg"])
        training_completion = _find_numeric(ctx, ["cumplimiento_practicas", "practice_completion", "entrenamiento_completado", "training_completion"])
        has_training_data = bool(practice_rows) or training_avg is not None or training_completion is not None
        top_program_name, top_program_total = _top_program(ctx)
        trend_delta = _trend_delta_percent(ctx)
        focus = re.sub(r"\s+", " ", str(task_text or "")).strip().lower()
        focus_calificaciones = "calificacion" in focus or "positiva" in focus or "positivas" in focus
        focus_comparativa = "comparativa" in focus or "sistemas vs" in focus
        focus_sistemas = "sistema" in focus
        focus_tendencia = "tendencia" in focus or "trend" in focus
        focus_cobertura = "cobertura" in focus or "adopcion" in focus or "uso" in focus
        focus_practicas = "practica" in focus or "entrenamiento" in focus or "resultado" in focus or "puntaje" in focus

        sistemas_row = None
        for row in program_rows:
            programa_name = str(row.get("programa") or row.get("nombre") or "").lower()
            if "sistema" in programa_name:
                sistemas_row = row
                break

        resumen: list[str] = []
        alertas: list[str] = []
        acciones: list[str] = []

        if total_consultas is not None and estudiantes_unicos is not None:
            resumen.append(
                f"Se registran {_fmt_number(total_consultas, 0)} consultas de {_fmt_number(estudiantes_unicos, 0)} estudiantes unicos en el periodo filtrado; este hallazgo describe uso de la plataforma y permite priorizar seguimiento por cobertura y participacion." 
            )
        elif total_consultas is not None:
            resumen.append(
                f"Se registran {_fmt_number(total_consultas, 0)} consultas en el periodo filtrado; no hay conteo consolidado de estudiantes unicos para estimar alcance real por usuario."
            )
        else:
            resumen.append(
                "No hay dato de total de consultas en el contexto cargado; sin este indicador no se puede cuantificar uso global del asistente."
            )

        if focus_sistemas and sistemas_row and isinstance(sistemas_row.get("total"), (int, float)):
            sistemas_total = float(sistemas_row.get("total"))
            total_programas = sum(float(r.get("total")) for r in program_rows if isinstance(r.get("total"), (int, float)))
            base = total_programas if total_programas > 0 else (float(total_consultas) if total_consultas else 0.0)
            share = (sistemas_total / base * 100.0) if base > 0 else 0.0
            resumen.append(
                f"Para el enfoque en Sistemas, el programa registra {_fmt_number(sistemas_total, 0)} interacciones y una participacion de {_fmt_number(share)}% dentro del bloque comparativo disponible; este dato permite contrastar uso frente a los demas programas con evidencia directa."
            )
        elif top_program_name and top_program_total is not None:
            resumen.append(
                f"En distribucion por programa, {top_program_name} concentra {_fmt_number(top_program_total, 0)} interacciones; este dato proviene del bloque 'programas' y permite comparar concentracion de uso frente a otras facultades."
            )
        elif program_rows:
            resumen.append(
                "Hay distribucion por programa disponible, pero no se pudo identificar un lider numerico consistente en los registros recibidos."
            )
        else:
            resumen.append(
                "No hay detalle por programa en el contexto; por ello no es posible una comparativa de uso entre Sistemas y los demas programas en este corte."
            )

        if consultas_hoy is not None and total_consultas is not None and float(total_consultas) > 0:
            peso_hoy = (float(consultas_hoy) / float(total_consultas)) * 100.0
            alertas.append(
                f"Las consultas de hoy representan {_fmt_number(peso_hoy)}% del acumulado ({_fmt_number(consultas_hoy, 0)} de {_fmt_number(total_consultas, 0)}); este porcentaje es sensible a picos diarios y conviene monitorearlo para capacidad operativa."
            )
        elif consultas_hoy is not None:
            alertas.append(
                f"Se reportan {_fmt_number(consultas_hoy, 0)} consultas hoy, pero no hay total de referencia para dimensionar su peso relativo en el periodo."
            )

        if has_training_data:
            practice_signal_parts = []
            if training_avg is not None:
                practice_signal_parts.append(f"promedio de practicas {_fmt_number(training_avg)}")
            if training_completion is not None:
                practice_signal_parts.append(f"cumplimiento {_fmt_percent(training_completion)}")
            if practice_rows:
                practice_signal_parts.append(f"{_fmt_number(len(practice_rows), 0)} registros de resultados")
            signal_text = ", ".join(practice_signal_parts)
            alertas.append(
                f"Se detectan datos de entrenamiento/practica ({signal_text}); al cruzarlos con uso por programa, se puede priorizar acompanamiento en cohortes con menor avance real."
            )
        else:
            alertas.append(
                "No hay resultados de entrenamientos/practicas en el contexto actual; por tanto, este informe describe uso de plataforma, pero no permite concluir progreso academico de los estudiantes."
            )

        if trend_delta is not None:
            direction = "crecimiento" if trend_delta >= 0 else "caida"
            if focus_tendencia:
                alertas.append(
                    f"En el enfoque de tendencia, la serie reporta {direction} de {_fmt_number(abs(trend_delta))}% entre el primer y ultimo punto; este movimiento exige seguimiento por programa para distinguir crecimiento sostenido de variaciones puntuales."
                )
            else:
                alertas.append(
                    f"La serie de tendencia muestra {direction} de {_fmt_number(abs(trend_delta))}% entre el primer y el ultimo punto disponible; este calculo se deriva solo de los valores enviados en 'tendencia'."
                )
        elif trend_rows:
            alertas.append(
                "Existe tendencia, pero no hay suficientes puntos numericos para calcular variacion entre inicio y cierre del periodo."
            )

        if topic_rows:
            top_topic = None
            for row in topic_rows:
                total = row.get("total")
                if not isinstance(total, (int, float)):
                    continue
                if top_topic is None or float(total) > float(top_topic.get("total", 0)):
                    top_topic = row
            if top_topic is not None:
                topic_name = str(top_topic.get("competencia") or top_topic.get("tema") or "tema principal")
                alertas.append(
                    f"El tema con mayor volumen es {topic_name} con {_fmt_number(top_topic.get('total'), 0)} registros; este dato representa frecuencia de consulta, no puntaje academico de desempeno."
                )
        else:
            alertas.append(
                "No hay bloque de temas_top en el contexto, por lo que no se puede priorizar contenidos por frecuencia de consulta."
            )

        if total_estudiantes is not None and estudiantes_unicos is not None and float(total_estudiantes) > 0:
            cobertura = (float(estudiantes_unicos) / float(total_estudiantes)) * 100.0
            if focus_cobertura:
                acciones.append(
                    f"Para el enfoque de cobertura/adopcion, fija meta semanal para elevar uso desde {_fmt_number(cobertura)}% ({_fmt_number(estudiantes_unicos, 0)}/{_fmt_number(total_estudiantes, 0)}) y audita avance diario por programa con responsable nominal."
                )
            else:
                acciones.append(
                    f"Definir meta semanal de cobertura para subir uso desde {_fmt_number(cobertura)}% ({_fmt_number(estudiantes_unicos, 0)}/{_fmt_number(total_estudiantes, 0)}) con seguimiento diario por programa y responsable asignado."
                )
        else:
            acciones.append(
                "Consolidar censo de total_estudiantes por programa para medir cobertura real; sin denominador institucional no es posible estimar penetracion del asistente con precision."
            )

        if not has_training_data:
            if focus_practicas:
                acciones.append(
                    "Dado el enfoque en practicas/entrenamientos, prioriza integrar resultados por estudiante (puntaje, avance, finalizacion y fecha) para habilitar comparativas de progreso real y no solo indicadores de uso."
                )
            else:
                acciones.append(
                    "Incorporar en analytics_context un bloque de resultados de practicas (puntaje, avance y finalizacion por estudiante/programa) para habilitar decisiones sobre impacto academico y no solo sobre adopcion de uso."
                )

        if program_rows:
            if focus_sistemas and sistemas_row and isinstance(sistemas_row.get("total"), (int, float)):
                sistemas_total = float(sistemas_row.get("total"))
                otros_total = sum(float(r.get("total")) for r in program_rows if isinstance(r.get("total"), (int, float))) - sistemas_total
                acciones.append(
                    f"Publicar comparativo semanal de Sistemas vs otros programas (Sistemas: {_fmt_number(sistemas_total, 0)}; Otros: {_fmt_number(otros_total, 0)}) para monitorear concentracion de uso y ajustar estrategia de difusion por facultad."
                )
            else:
                acciones.append(
                    "Publicar comparativo semanal por programa (consultas y participacion relativa) usando solo el bloque programas actual, para identificar subutilizacion y activar acompanamiento focalizado."
                )
        else:
            acciones.append(
                "Habilitar captura por programa en el pipeline analitico para responder comparativas solicitadas con evidencia cuantitativa verificable."
            )

        focus_original = re.sub(r"\s+", " ", str(task_text or "")).strip()
        if focus_original:
            acciones.append(
                f"Mantener el enfoque solicitado ({focus_original[:140]}) y limitar decisiones a variables presentes en el contexto; cualquier recomendacion adicional debe etiquetarse como dato faltante, no como conclusion inferida."
            )

        def _merge_priority(priority_items: list[str], base_items: list[str]) -> list[str]:
            merged: list[str] = []
            for item in priority_items + base_items:
                text_item = re.sub(r"\s+", " ", str(item or "")).strip()
                if not text_item:
                    continue
                if text_item in merged:
                    continue
                merged.append(text_item)
            return merged[:3]

        primary_focus = "auto"
        if focus_practicas:
            primary_focus = "practicas"
        elif focus_calificaciones:
            primary_focus = "calificaciones"
        elif focus_tendencia:
            primary_focus = "tendencia"
        elif focus_sistemas or focus_comparativa:
            primary_focus = "comparativa"
        elif focus_cobertura:
            primary_focus = "cobertura"

        if primary_focus == "comparativa":
            comp_resumen: list[str] = []
            comp_alertas: list[str] = []
            comp_acciones: list[str] = []

            if program_rows:
                ranked = sorted(
                    [r for r in program_rows if isinstance(r.get("total"), (int, float))],
                    key=lambda r: float(r.get("total", 0)),
                    reverse=True,
                )
                total_programas = sum(float(r.get("total", 0)) for r in ranked)
                if ranked:
                    top_name = str(ranked[0].get("programa") or ranked[0].get("nombre") or "programa lider")
                    top_total = float(ranked[0].get("total", 0))
                    top_share = (top_total / total_programas * 100.0) if total_programas > 0 else 0.0
                    comp_resumen.append(
                        f"Comparativa por programas: {top_name} lidera con {_fmt_number(top_total, 0)} consultas y {_fmt_number(top_share)}% de participacion sobre el total del bloque 'programas'."
                    )
                if len(ranked) >= 2:
                    second_name = str(ranked[1].get("programa") or ranked[1].get("nombre") or "segundo programa")
                    gap = float(ranked[0].get("total", 0)) - float(ranked[1].get("total", 0))
                    comp_alertas.append(
                        f"La brecha entre el primer y segundo programa es de {_fmt_number(gap, 0)} consultas ({top_name} vs {second_name}); esta concentracion sugiere uso desigual entre facultades."
                    )
                if sistemas_row and isinstance(sistemas_row.get("total"), (int, float)):
                    sistemas_total = float(sistemas_row.get("total"))
                    otros_total = max(total_programas - sistemas_total, 0.0)
                    comp_acciones.append(
                        f"Instalar tablero semanal de Sistemas vs Otros (Sistemas {_fmt_number(sistemas_total, 0)} | Otros {_fmt_number(otros_total, 0)}) y definir meta de cierre de brecha por programa."
                    )
            else:
                comp_alertas.append("No hay datos por programa para una comparativa valida; no se puede estimar concentracion relativa entre Sistemas y otras facultades.")
                comp_acciones.append("Habilitar captura consistente del bloque 'programas' para comparar adopcion por facultad con evidencia cuantitativa.")

            resumen = _merge_priority(comp_resumen, resumen)
            alertas = _merge_priority(comp_alertas, alertas)
            acciones = _merge_priority(comp_acciones, acciones)

        elif primary_focus == "tendencia":
            trend_resumen: list[str] = []
            trend_alertas: list[str] = []
            trend_acciones: list[str] = []

            if trend_rows and trend_delta is not None:
                direction = "crece" if trend_delta >= 0 else "cae"
                first_total = trend_rows[0].get("total")
                last_total = trend_rows[-1].get("total")
                trend_resumen.append(
                    f"Tendencia prioritaria: el volumen {direction} de {_fmt_number(abs(trend_delta))}% (de {_fmt_number(first_total, 0)} a {_fmt_number(last_total, 0)}) entre el primer y ultimo punto de la serie enviada."
                )
                max_point = max((r for r in trend_rows if isinstance(r.get("total"), (int, float))), key=lambda r: float(r.get("total", 0)), default=None)
                if max_point:
                    trend_alertas.append(
                        f"El pico de actividad se ubica en {str(max_point.get('fecha') or 'fecha no informada')} con {_fmt_number(max_point.get('total'), 0)} consultas; conviene revisar capacidad operativa en esos picos."
                    )
                trend_acciones.append("Programar seguimiento diario de variacion (% dia vs dia) y activar alerta temprana cuando la pendiente cambie bruscamente en dos cortes consecutivos.")
            else:
                trend_alertas.append("No hay serie de tendencia suficiente para evaluar dinamica temporal; solo es posible una foto estatica de volumen total.")
                trend_acciones.append("Completar al menos 7 puntos de tendencia para habilitar analisis de aceleracion, estacionalidad y picos operativos.")

            resumen = _merge_priority(trend_resumen, resumen)
            alertas = _merge_priority(trend_alertas, alertas)
            acciones = _merge_priority(trend_acciones, acciones)

        elif primary_focus == "cobertura":
            cov_resumen: list[str] = []
            cov_alertas: list[str] = []
            cov_acciones: list[str] = []

            if total_estudiantes is not None and estudiantes_unicos is not None and float(total_estudiantes) > 0:
                cobertura = (float(estudiantes_unicos) / float(total_estudiantes)) * 100.0
                cov_resumen.append(
                    f"Cobertura prioritaria: el asistente alcanza {_fmt_number(cobertura)}% de la base estudiantil ({_fmt_number(estudiantes_unicos, 0)}/{_fmt_number(total_estudiantes, 0)}), indicador central para gestion de adopcion."
                )
                cov_alertas.append("Cobertura por debajo de 100% implica estudiantes sin uso del canal; la interpretacion de impacto academico es parcial mientras no se cierre esa brecha de acceso.")
                cov_acciones.append("Definir metas de activacion por programa y cohorte para incrementar cobertura semanal, con responsables y reporte diario de conversion.")
            else:
                cov_alertas.append("Sin total_estudiantes o estudiantes_unicos no se puede calcular cobertura real; falta denominador para evaluar alcance institucional.")
                cov_acciones.append("Completar metrica de poblacion objetivo por programa para calcular cobertura y no depender solo de volumen de consultas.")

            resumen = _merge_priority(cov_resumen, resumen)
            alertas = _merge_priority(cov_alertas, alertas)
            acciones = _merge_priority(cov_acciones, acciones)

        elif primary_focus == "practicas":
            prac_resumen: list[str] = []
            prac_alertas: list[str] = []
            prac_acciones: list[str] = []

            if has_training_data:
                parts: list[str] = []
                if training_avg is not None:
                    parts.append(f"promedio {_fmt_number(training_avg)}")
                if training_completion is not None:
                    parts.append(f"cumplimiento {_fmt_percent(training_completion)}")
                if practice_rows:
                    parts.append(f"{_fmt_number(len(practice_rows), 0)} registros")
                prac_resumen.append(
                    f"Enfoque practicas: hay datos de entrenamiento ({', '.join(parts)}), suficientes para iniciar priorizacion por avance real y no solo por volumen de uso."
                )
                prac_alertas.append("Aun con datos de practicas, se requiere consistencia por estudiante/programa para evitar sesgos por registros incompletos.")
                prac_acciones.append("Cruzar resultados de practica con uso por programa y generar ranking semanal de avance para focalizar tutoria academica.")
            else:
                prac_resumen.append("Enfoque practicas: el contexto no incluye resultados de entrenamiento, por lo que no se puede medir progreso academico real.")
                prac_alertas.append("Sin puntajes, avance o finalizacion de practicas, cualquier conclusion sobre efectividad academica seria especulativa.")
                prac_acciones.append("Prioridad 1: enviar bloque de resultados de practica por estudiante/programa (puntaje, avance, finalizacion y fecha) antes de emitir recomendaciones de rendimiento.")

            resumen = _merge_priority(prac_resumen, resumen)
            alertas = _merge_priority(prac_alertas, alertas)
            acciones = _merge_priority(prac_acciones, acciones)

        elif primary_focus == "calificaciones":
            rate_resumen: list[str] = []
            rate_alertas: list[str] = []
            rate_acciones: list[str] = []

            if promedio_positivas is not None:
                rate_resumen.append(
                    f"La metrica de calificaciones positivas disponible en el contexto es {_fmt_number(promedio_positivas)}%."
                )
                if filtro_es_global:
                    rate_resumen.append(
                        "Ese porcentaje corresponde al agregado del filtro actual (Todos los programas), no a un programa especifico."
                    )
                    rate_alertas.append(
                        "Con los datos actuales no existe desglose de calificaciones positivas por programa; por eso no se puede afirmar de que programa viene ese porcentaje global."
                    )
                    rate_acciones.append(
                        "Agregar al contexto un bloque de calificacion_por_programa para responder comparativas (Sistemas vs otros) sobre porcentaje positivo de forma trazable."
                    )
                else:
                    rate_resumen.append(
                        f"Como hay filtro por programa ({filtro_programa}), el porcentaje se interpreta para ese programa dentro del periodo consultado."
                    )
                    rate_acciones.append(
                        f"Mantener el filtro en {filtro_programa} y comparar periodos para verificar si la calificacion positiva mejora o cae con el tiempo."
                    )
            else:
                rate_alertas.append(
                    "No hay metrica de calificaciones positivas en analytics_context para responder ese punto de manera cuantitativa."
                )
                rate_acciones.append(
                    "Incluir promedioPositivas en metricas del contexto para habilitar respuesta directa sobre porcentaje positivo."
                )

            resumen = _merge_priority(rate_resumen, resumen)
            alertas = _merge_priority(rate_alertas, alertas)
            acciones = _merge_priority(rate_acciones, acciones)

        return (resumen[:3], alertas[:3], acciones[:3])

    def _finalize_section(model_items: list[str], grounded_items: list[str]) -> list[str]:
        model_clean: list[str] = []
        for item in (model_items or []):
            text_item = re.sub(r"\s+", " ", str(item or "")).strip()
            if not text_item:
                continue
            if text_item in model_clean:
                continue
            model_clean.append(text_item)
            if len(model_clean) == 3:
                break

        # Si el modelo entrego contenido suficiente, evitar "relleno" deterministico repetitivo.
        if len(model_clean) >= 2:
            return model_clean

        merged = list(model_clean)
        for item in (grounded_items or []):
            text_item = re.sub(r"\s+", " ", str(item or "")).strip()
            if not text_item or text_item in merged:
                continue
            merged.append(text_item)
            if len(merged) == 3:
                break
        return merged

    def _estimate_context_volume(ctx: dict) -> dict:
        if not isinstance(ctx, dict):
            return {"metric_keys": 0, "list_blocks": 0, "total_rows": 0}

        metricas = ctx.get("metricas") if isinstance(ctx.get("metricas"), dict) else {}
        list_blocks = 0
        total_rows = 0
        for value in ctx.values():
            if isinstance(value, list):
                list_blocks += 1
                total_rows += len(value)

        return {
            "metric_keys": len(metricas.keys()),
            "list_blocks": list_blocks,
            "total_rows": total_rows,
        }

    try:
        started_at = time.perf_counter()
        # Base deterministica para mantener trazabilidad y evitar alucinaciones.
        grounded_resumen, grounded_alertas, grounded_acciones = _build_grounded_admin_blocks(analytics_context or {}, task)
        context_volume = _estimate_context_volume(analytics_context or {})

        grounded_seed = {
            "resumen_base": grounded_resumen,
            "alertas_base": grounded_alertas,
            "acciones_base": grounded_acciones,
        }
        grounded_seed_json = json.dumps(grounded_seed, ensure_ascii=False)

        enriched_prompt = (
            "Eres director de analitica academica para una universidad y redactas briefings ejecutivos para coordinacion Saber Pro.\n"
            "Debes sintetizar con precision, sin inventar cifras y con foco en decisiones institucionales de corto plazo.\n"
            "Usa EXCLUSIVAMENTE los datos del contexto y del bloque BASE_VERIFICADA.\n"
            "Si falta un dato, no completes con supuestos: declara la brecha y su impacto.\n\n"
            "Debes cruzar explicitamente multiples fuentes del contexto (metricas, programas, tendencia, temas y practicas cuando existan).\n"
            "Devuelve SOLO JSON valido con esta estructura exacta:\n"
            "{\n"
            "  \"resumen\": [\"...\", \"...\"],\n"
            "  \"alertas\": [\"...\", \"...\"],\n"
            "  \"acciones\": [\"...\", \"...\"]\n"
            "}\n\n"
            "Reglas de calidad:\n"
            "- Maximo 3 items por lista.\n"
            "- Cada item entre 18 y 32 palabras, claro y sin relleno.\n"
            "- Cada item debe incluir: hallazgo (dato), impacto institucional y accion o implicacion operativa.\n"
            "- En 'acciones', prioriza medidas ejecutables en 7 dias, con verbo de accion al inicio.\n"
            "- Evita frases vagas (por ejemplo: 'mejorar procesos' sin decir como).\n"
            "- Evita repetir literalmente frases de BASE_VERIFICADA salvo que sea estrictamente necesario.\n"
            "- Sin markdown ni texto fuera del JSON.\n\n"
            f"CONTEXTO_ANALITICO (JSON):\n{context_json}\n\n"
            f"BASE_VERIFICADA (JSON):\n{grounded_seed_json}\n\n"
            f"TAREA_DEL_COORDINADOR:\n{task}\n"
        )

        def _run_enriched():
            model = get_gemini_model()
            return model.generate_content(enriched_prompt)

        resp = await loop.run_in_executor(None, _run_enriched)
        text = _extract_text(resp).strip()
        data = _parse_json_relaxed(text) or {}

        # Si el modelo devolvió un JSON encapsulado como string dentro de "resumen".
        if isinstance(data.get("resumen"), str):
            nested = _parse_json_relaxed(str(data.get("resumen")))
            if nested and any(k in nested for k in ("resumen", "alertas", "acciones")):
                data = nested

        # Si no hay bloques detectables, intentar leerlos directamente del texto crudo.
        if not any(k in data for k in ("resumen", "alertas", "acciones")):
            nested_from_text = _parse_json_relaxed(text)
            if nested_from_text:
                data = nested_from_text

        # Caso donde una seccion trae dentro el JSON completo serializado.
        nested_payload = (
            _extract_nested_payload(data.get("resumen"))
            or _extract_nested_payload(data.get("alertas"))
            or _extract_nested_payload(data.get("acciones"))
        )
        if nested_payload:
            data = nested_payload

        model_resumen = _normalize_points(data.get("resumen"))
        model_alertas = _normalize_points(data.get("alertas"))
        model_acciones = _normalize_points(data.get("acciones"))

        # Caso raro: el modelo devuelve el objeto completo serializado dentro de una lista.
        def _unwrap_nested_object(items: list[str]) -> dict | None:
            for item in items:
                nested = _parse_json_relaxed(item)
                if nested and any(k in nested for k in ("resumen", "alertas", "acciones")):
                    return nested
            return None

        nested_from_blocks = _unwrap_nested_object(model_resumen) or _unwrap_nested_object(model_alertas) or _unwrap_nested_object(model_acciones)
        if nested_from_blocks:
            model_resumen = _normalize_points(nested_from_blocks.get("resumen"))
            model_alertas = _normalize_points(nested_from_blocks.get("alertas"))
            model_acciones = _normalize_points(nested_from_blocks.get("acciones"))

        # Sanitizacion final para evitar entregar bloques con JSON crudo en texto.
        model_resumen = _normalize_points(_clean_contaminated_items(model_resumen, "resumen"))
        model_alertas = _normalize_points(_clean_contaminated_items(model_alertas, "alertas"))
        model_acciones = _normalize_points(_clean_contaminated_items(model_acciones, "acciones"))

        if any(_is_contaminated_item(item) for item in (model_resumen + model_alertas + model_acciones)):
            model_resumen, model_alertas, model_acciones = [], [], []

        # Fallback defensivo si el modelo no respeta el JSON.
        if not (model_resumen or model_alertas or model_acciones):
            raw_text = re.sub(r"\s+", " ", str(text or "")).strip()
            malformed_json_like = (
                ("{" in raw_text or "[" in raw_text)
                and any(k in raw_text.lower() for k in ("resumen", "alertas", "acciones"))
            )
            if malformed_json_like:
                model_resumen, model_alertas, model_acciones = [], [], []
            else:
                model_resumen = [raw_text] if raw_text else []

        # Ensamble final: primero lo que aporta la IA, luego respaldo deterministico.
        resumen = _finalize_section(model_resumen, grounded_resumen)
        alertas = _finalize_section(model_alertas, grounded_alertas)
        acciones = _finalize_section(model_acciones, grounded_acciones)

        if not (resumen or alertas or acciones):
            resumen, alertas, acciones = grounded_resumen, grounded_alertas, grounded_acciones

        resumen_latex = [_latex_escape_text(item) for item in resumen]
        alertas_latex = [_latex_escape_text(item) for item in alertas]
        acciones_latex = [_latex_escape_text(item) for item in acciones]

        latex_lines = ["\\begin{aligned}"]
        latex_lines.extend(_build_section("Resumen Ejecutivo:", resumen_latex))
        latex_lines.extend(_build_section("Alertas Clave:", alertas_latex))
        latex_lines.extend(_build_section("Acciones (7 dias):", acciones_latex, add_break_after=False))
        latex_lines.append("\\end{aligned}")

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "latex": "".join(latex_lines),
            "resumen": resumen,
            "alertas": alertas,
            "acciones": acciones,
            "analysis_meta": {
                "mode": "hybrid_model_first",
                "latency_ms": elapsed_ms,
                "context_volume": context_volume,
                "model_items": {
                    "resumen": len(model_resumen),
                    "alertas": len(model_alertas),
                    "acciones": len(model_acciones),
                },
                "final_items": {
                    "resumen": len(resumen),
                    "alertas": len(alertas),
                    "acciones": len(acciones),
                },
            },
        }
    except Exception:
        return {
            "latex": "\\begin{aligned}\\text{No se pudo generar analisis en este momento.}\\end{aligned}",
            "resumen": ["No se pudo generar analisis en este momento"],
            "alertas": [],
            "acciones": [],
            "analysis_meta": {
                "mode": "error",
                "latency_ms": None,
                "context_volume": _estimate_context_volume(analytics_context or {}),
            },
        }


async def generate_admin_analytics_report(task: str, analytics_context: dict) -> dict:
    """Motor v2 de informe estrategico para coordinacion (formato documento)."""

    def _as_float(value) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            txt = value.replace("%", "").replace(",", ".").strip()
            try:
                return float(txt)
            except Exception:
                return None
        return None

    def _as_list(value) -> list:
        return value if isinstance(value, list) else []

    def _ctx_list(ctx: dict, keys: list[str]) -> list:
        for key in keys:
            value = ctx.get(key)
            if isinstance(value, list):
                return value
        return []

    def _fmt_num(value: float | None, decimals: int = 1) -> str:
        if value is None:
            return "s/d"
        return f"{value:.{decimals}f}"

    def _fmt_pct(value: float | None) -> str:
        if value is None:
            return "s/d"
        v = float(value)
        if 0 <= v <= 1:
            v *= 100
        return f"{v:.1f}%"

    def _context_volume(ctx: dict) -> dict:
        metricas = ctx.get("metricas") if isinstance(ctx.get("metricas"), dict) else {}
        list_blocks = 0
        total_rows = 0
        for value in ctx.values():
            if isinstance(value, list):
                list_blocks += 1
                total_rows += len(value)
        return {
            "metric_keys": len(metricas.keys()),
            "list_blocks": list_blocks,
            "total_rows": total_rows,
        }

    def _sanitize_lines(value, max_items: int = 4) -> list[str]:
        if not isinstance(value, list):
            return []
        clean: list[str] = []
        for raw in value:
            txt = re.sub(r"\s+", " ", str(raw or "")).strip()
            if not txt:
                continue
            if txt in clean:
                continue
            clean.append(txt)
            if len(clean) >= max_items:
                break
        return clean

    def _sanitize_plan(value, max_items: int = 4) -> list[dict]:
        if not isinstance(value, list):
            return []
        clean: list[dict] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            accion = re.sub(r"\s+", " ", str(item.get("accion") or "")).strip()
            responsable = re.sub(r"\s+", " ", str(item.get("responsable") or "")).strip()
            kpi = re.sub(r"\s+", " ", str(item.get("kpi") or "")).strip()
            plazo = re.sub(r"\s+", " ", str(item.get("plazo") or "")).strip()
            if not accion:
                continue
            clean.append({
                "accion": accion,
                "responsable": responsable or "Coordinacion academica",
                "kpi": kpi or "Definir indicador de avance semanal",
                "plazo": plazo or "7 dias",
            })
            if len(clean) >= max_items:
                break
        return clean

    def _build_fallback_document(evidence: dict, filters: dict, task_text: str) -> dict:
        contexto_general = (
            f"Corte analizado con programa={filters.get('programa', 'Todos')} y rango "
            f"{filters.get('fecha_inicio', 'sin filtro')} a {filters.get('fecha_fin', 'sin filtro')}. "
            f"Se registran {evidence.get('total_consultas_text', 's/d')} consultas de "
            f"{evidence.get('estudiantes_unicos_text', 's/d')} estudiantes unicos."
        )

        hallazgos = [
            (
                f"Cobertura institucional estimada en {evidence.get('cobertura_text', 's/d')} "
                f"sobre la poblacion objetivo ({evidence.get('estudiantes_unicos_text', 's/d')} de "
                f"{evidence.get('total_estudiantes_text', 's/d')})."
            ),
            (
                f"Programa con mayor volumen: {evidence.get('top_program_name', 's/d')} "
                f"con {evidence.get('top_program_total_text', 's/d')} consultas "
                f"({evidence.get('top_program_share_text', 's/d')} del total por programa)."
            ),
            (
                f"Tendencia del periodo: variacion de {evidence.get('trend_delta_text', 's/d')} "
                f"entre el primer y ultimo punto, con pico de {evidence.get('trend_peak_total_text', 's/d')} "
                f"en {evidence.get('trend_peak_date', 'fecha no informada')}."
            ),
        ]

        riesgos = [
            (
                "La concentracion de uso en pocos programas puede sesgar la lectura institucional "
                "si no se incrementa la adopcion en facultades con baja participacion."
            ),
            (
                "Sin estandar de seguimiento de practicas por cohorte, la mejora academica puede "
                "quedar en actividad operativa sin impacto medible."
            ),
            (
                "Si faltan bloques de datos en el contexto, cualquier comparativa de desempeno "
                "debe tratarse como preliminar y no como conclusion final."
            ),
        ]

        plan = [
            {
                "accion": "Instalar tablero semanal de seguimiento por programa con semaforo de cobertura, tendencia y practicas.",
                "responsable": "Coordinacion academica + analitica",
                "kpi": "Programas con cobertura >= 70% y reporte semanal publicado",
                "plazo": "7 dias",
            },
            {
                "accion": "Activar plan focalizado en los dos programas con menor participacion para elevar uso del asistente.",
                "responsable": "Lideres de programa",
                "kpi": "Incremento de consultas por programa de al menos 15% semana a semana",
                "plazo": "7 dias",
            },
            {
                "accion": "Cruzar practicas y tendencia para detectar cohortes con alta actividad pero bajo desempeno y definir intervencion corta.",
                "responsable": "Coordinacion de permanencia",
                "kpi": "Cohortes criticas identificadas y plan de intervencion emitido",
                "plazo": "7 dias",
            },
        ]

        vacios = [
            "Desagregacion de calificacion positiva por programa para comparativas de calidad.",
            "Cobertura por cohorte/semestre para evaluar adopcion real por segmento.",
            "Serie historica de practicas con consistencia de intento, acierto y nivel por estudiante.",
        ]

        return {
            "contexto_general": contexto_general,
            "hallazgos_clave": hallazgos,
            "riesgos_prioritarios": riesgos,
            "plan_7_dias": plan,
            "vacios_de_dato": vacios,
            "foco_solicitado": re.sub(r"\s+", " ", str(task_text or "")).strip()[:240],
        }

    started_at = time.perf_counter()
    ctx = analytics_context if isinstance(analytics_context, dict) else {}
    filters = ctx.get("filtros") if isinstance(ctx.get("filtros"), dict) else {}
    metricas = ctx.get("metricas") if isinstance(ctx.get("metricas"), dict) else {}

    programas = _ctx_list(ctx, ["programas", "por_programa", "programas_top"])
    tendencia = _ctx_list(ctx, ["tendencia", "trend", "serie_tiempo"])
    temas = _ctx_list(ctx, ["temas_top", "temas", "topics"])
    practicas = _ctx_list(ctx, ["resultados_practicas", "practicas_resultados", "practice_results"])
    competencias = _ctx_list(ctx, ["promedio_competencias", "practice_competencies", "competencias"])
    niveles = _ctx_list(ctx, ["evolucion_nivel", "level_progression", "nivel"])

    total_consultas = _as_float(metricas.get("totalConsultas")) or _as_float(metricas.get("total_consultas"))
    estudiantes_unicos = _as_float(metricas.get("estudiantesUnicos")) or _as_float(metricas.get("estudiantes_unicos"))
    total_estudiantes = _as_float(metricas.get("totalEstudiantes")) or _as_float(metricas.get("total_estudiantes"))
    consultas_hoy = _as_float(metricas.get("consultasHoy")) or _as_float(metricas.get("consultas_hoy"))
    promedio_positivas = _as_float(metricas.get("promedioPositivas")) or _as_float(metricas.get("promedio_positivas"))

    top_program_name = "s/d"
    top_program_total = None
    total_programas = 0.0
    if programas:
        rows = [r for r in programas if isinstance(r, dict)]
        ranked = []
        for row in rows:
            total = _as_float(row.get("total"))
            if total is None:
                continue
            ranked.append((str(row.get("programa") or row.get("nombre") or "Programa"), total))
            total_programas += total
        ranked.sort(key=lambda x: x[1], reverse=True)
        if ranked:
            top_program_name, top_program_total = ranked[0]

    trend_delta = None
    trend_peak_date = "fecha no informada"
    trend_peak_total = None
    trend_numeric = [r for r in tendencia if isinstance(r, dict) and _as_float(r.get("total")) is not None]
    if len(trend_numeric) >= 2:
        first_total = _as_float(trend_numeric[0].get("total"))
        last_total = _as_float(trend_numeric[-1].get("total"))
        if first_total is not None and last_total is not None and first_total != 0:
            trend_delta = ((last_total - first_total) / first_total) * 100.0
    if trend_numeric:
        peak_row = max(trend_numeric, key=lambda r: _as_float(r.get("total")) or 0.0)
        trend_peak_total = _as_float(peak_row.get("total"))
        trend_peak_date = str(peak_row.get("fecha") or "fecha no informada")

    top_topic = "s/d"
    top_topic_total = None
    topic_numeric = [r for r in temas if isinstance(r, dict) and _as_float(r.get("total")) is not None]
    if topic_numeric:
        best_topic = max(topic_numeric, key=lambda r: _as_float(r.get("total")) or 0.0)
        top_topic = str(best_topic.get("competencia") or best_topic.get("tema") or "tema principal")
        top_topic_total = _as_float(best_topic.get("total"))

    practice_weighted = None
    total_attempts = 0.0
    weighted_sum = 0.0
    for row in practicas:
        if not isinstance(row, dict):
            continue
        intentos = _as_float(row.get("intentos")) or 0.0
        score = _as_float(row.get("puntaje_promedio"))
        if intentos <= 0 or score is None:
            continue
        total_attempts += intentos
        weighted_sum += intentos * score
    if total_attempts > 0:
        practice_weighted = weighted_sum / total_attempts

    weakest_comp = None
    weakest_comp_score = None
    comp_numeric = [r for r in competencias if isinstance(r, dict) and _as_float(r.get("promedio_competencia")) is not None]
    if comp_numeric:
        weak = min(comp_numeric, key=lambda r: _as_float(r.get("promedio_competencia")) or 0.0)
        weakest_comp = str(weak.get("competencia") or "competencia")
        weakest_comp_score = _as_float(weak.get("promedio_competencia"))

    avg_level = None
    level_rows = [r for r in niveles if isinstance(r, dict) and _as_float(r.get("nivel_promedio")) is not None]
    if level_rows:
        avg_level = sum((_as_float(r.get("nivel_promedio")) or 0.0) for r in level_rows) / len(level_rows)

    cobertura = None
    if total_estudiantes and total_estudiantes > 0 and estudiantes_unicos is not None:
        cobertura = (estudiantes_unicos / total_estudiantes) * 100.0

    top_program_share = None
    if top_program_total is not None and total_programas > 0:
        top_program_share = (top_program_total / total_programas) * 100.0

    evidence = {
        "total_consultas": total_consultas,
        "estudiantes_unicos": estudiantes_unicos,
        "total_estudiantes": total_estudiantes,
        "consultas_hoy": consultas_hoy,
        "promedio_positivas": promedio_positivas,
        "cobertura": cobertura,
        "top_program_name": top_program_name,
        "top_program_total": top_program_total,
        "top_program_share": top_program_share,
        "trend_delta_percent": trend_delta,
        "trend_peak_date": trend_peak_date,
        "trend_peak_total": trend_peak_total,
        "top_topic": top_topic,
        "top_topic_total": top_topic_total,
        "practice_weighted_score": practice_weighted,
        "weakest_competency": weakest_comp,
        "weakest_competency_score": weakest_comp_score,
        "average_level": avg_level,
        "dataset_rows": {
            "programas": len(programas),
            "tendencia": len(tendencia),
            "temas": len(temas),
            "practicas": len(practicas),
            "competencias": len(competencias),
            "niveles": len(niveles),
        },
        "total_consultas_text": _fmt_num(total_consultas, 0),
        "estudiantes_unicos_text": _fmt_num(estudiantes_unicos, 0),
        "total_estudiantes_text": _fmt_num(total_estudiantes, 0),
        "cobertura_text": _fmt_pct(cobertura),
        "top_program_total_text": _fmt_num(top_program_total, 0),
        "top_program_share_text": _fmt_pct(top_program_share),
        "trend_delta_text": _fmt_pct(trend_delta),
        "trend_peak_total_text": _fmt_num(trend_peak_total, 0),
    }

    evidence_json = json.dumps(evidence, ensure_ascii=False)
    filters_json = json.dumps(filters, ensure_ascii=False)
    task_text = re.sub(r"\s+", " ", str(task or "")).strip()

    prompt = (
        "Eres un director de analitica academica y debes redactar un informe institucional para coordinacion Saber Pro.\n"
        "Tu salida debe parecer un documento tecnico ejecutivo, no bullets genericos.\n"
        "Usa SOLO la evidencia suministrada; no inventes cifras.\n"
        "Si falta dato, dilo como vacio de dato y su impacto.\n\n"
        "Devuelve SOLO JSON valido con esta estructura exacta:\n"
        "{\n"
        "  \"contexto_general\": \"...\",\n"
        "  \"hallazgos_clave\": [\"...\", \"...\", \"...\"],\n"
        "  \"riesgos_prioritarios\": [\"...\", \"...\", \"...\"],\n"
        "  \"plan_7_dias\": [\n"
        "    {\"accion\":\"...\",\"responsable\":\"...\",\"kpi\":\"...\",\"plazo\":\"...\"}\n"
        "  ],\n"
        "  \"vacios_de_dato\": [\"...\", \"...\"],\n"
        "  \"foco_solicitado\": \"...\"\n"
        "}\n\n"
        "Reglas estrictas:\n"
        "- 1 parrafo en contexto_general (40-80 palabras).\n"
        "- 3 a 4 hallazgos, cada uno con dato + impacto + implicacion de gestion.\n"
        "- 2 a 4 riesgos, concretos y accionables.\n"
        "- 3 a 4 acciones en plan_7_dias con responsable, KPI y plazo realista.\n"
        "- 2 a 4 vacios de dato priorizados.\n"
        "- Cruza al menos 3 bloques de evidencia (metricas, programas, tendencia, temas o practicas).\n"
        "- Sin markdown ni texto fuera del JSON.\n\n"
        f"EVIDENCIA_NORMALIZADA:\n{evidence_json}\n\n"
        f"FILTROS_ACTIVOS:\n{filters_json}\n\n"
        f"FOCO_SOLICITADO:\n{task_text or 'Informe general de coordinacion'}\n"
    )

    loop = asyncio.get_running_loop()

    def _run_model():
        model = get_gemini_model()
        return model.generate_content(prompt)

    model_raw = ""
    model_ok = False
    document = None

    try:
        resp = await loop.run_in_executor(None, _run_model)
        model_raw = _extract_text(resp).strip()
        parsed = _parse_json_relaxed(model_raw) or {}

        document_candidate = {
            "contexto_general": re.sub(r"\s+", " ", str(parsed.get("contexto_general") or "")).strip(),
            "hallazgos_clave": _sanitize_lines(parsed.get("hallazgos_clave"), 4),
            "riesgos_prioritarios": _sanitize_lines(parsed.get("riesgos_prioritarios"), 4),
            "plan_7_dias": _sanitize_plan(parsed.get("plan_7_dias"), 4),
            "vacios_de_dato": _sanitize_lines(parsed.get("vacios_de_dato"), 4),
            "foco_solicitado": re.sub(r"\s+", " ", str(parsed.get("foco_solicitado") or task_text)).strip()[:240],
        }

        if (
            document_candidate["contexto_general"]
            and len(document_candidate["hallazgos_clave"]) >= 2
            and len(document_candidate["plan_7_dias"]) >= 2
        ):
            document = document_candidate
            model_ok = True
    except Exception:
        model_ok = False

    if not document:
        document = _build_fallback_document(evidence, filters, task_text)

    resumen = _sanitize_lines([
        document.get("contexto_general", ""),
        *document.get("hallazgos_clave", []),
    ], 3)
    alertas = _sanitize_lines(document.get("riesgos_prioritarios", []), 3)
    acciones = _sanitize_lines([
        f"{p.get('accion', '')} Responsable: {p.get('responsable', '')}. KPI: {p.get('kpi', '')}. Plazo: {p.get('plazo', '')}."
        for p in _as_list(document.get("plan_7_dias"))
        if isinstance(p, dict)
    ], 3)

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    meta = {
        "mode": "document_v2_model_first" if model_ok else "document_v2_fallback",
        "latency_ms": elapsed_ms,
        "context_volume": _context_volume(ctx),
        "model_output_chars": len(model_raw),
        "sections": {
            "hallazgos": len(document.get("hallazgos_clave", [])),
            "riesgos": len(document.get("riesgos_prioritarios", [])),
            "plan": len(document.get("plan_7_dias", [])),
            "vacios": len(document.get("vacios_de_dato", [])),
        },
    }

    return {
        "latex": "",
        "resumen": resumen,
        "alertas": alertas,
        "acciones": acciones,
        "documento": document,
        "analysis_meta": meta,
    }
