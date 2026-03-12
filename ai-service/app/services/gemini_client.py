"""
Cliente Gemini Flash para generación de respuestas RAG.
RF-07: Envía contexto recuperado y genera respuesta con fuentes.
"""

import os
import asyncio
import threading
from typing import AsyncGenerator
import google.generativeai as genai
from functools import lru_cache

# Config para el chat RAG — respuestas conversacionales cortas
GENERATION_CONFIG = {
    "max_output_tokens": 900,
    "temperature": 0.2,
    "top_p": 0.80,
}

# Config para generación de preguntas de práctica — necesita más tokens para el JSON
GENERATION_CONFIG_QUIZ = {
    "max_output_tokens": 4096,
    "temperature": 0.4,
    "top_p": 0.90,
}


@lru_cache(maxsize=1)
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    return genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG)


def get_gemini_quiz_model():
    """Modelo con más tokens para generar preguntas de práctica en JSON."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    return genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG_QUIZ)


def _build_prompt(pregunta: str, contexto: list[dict], nombre: str = "") -> str:
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
            "- Si es una pregunta académica: explica apoyándote en el contexto oficial y cierra con UNA pregunta\n"
            "  que guíe el siguiente paso (ej: '¿Quieres que practiquemos un ejercicio de esto?').\n"
        )
    else:
        instruccion_contexto = (
            "- No tengo fragmentos específicos en este momento, pero tienes conocimiento profundo sobre Saber Pro.\n"
            "- Responde con contenido CONCRETO sobre el tema usando tu conocimiento general de Saber Pro.\n"
            "- NO preguntes qué quiere practicar si el mensaje ya especifica un tema — ¡ya te lo dijo!\n"
            "- Explica brevemente el tema pedido y cierra con una pregunta de práctica o profundización.\n"
        )

    return (
        f"Eres Saber Pro AI, el tutor personal de {nombre_corto} en la Universidad de Cundinamarca.\n"
        f"Acompañas a {nombre_corto} en su preparación para Saber Pro con cercanía y buen humor, no con formalidad.\n\n"
        "CÓMO RESPONDER:\n"
        f"- Llama a {nombre_corto} por su nombre de forma natural (una sola vez, al inicio o al cierre).\n"
        "- Máximo 3 párrafos cortos. Sin introducción larga. Directo al grano.\n"
        "- Si es un saludo o mensaje corto SIN tema específico: responde brevemente y PREGUNTA qué quiere repasar.\n"
        f"{instruccion_contexto}"
        "- Sin encabezados '### Título'. Sin listas largas. **Negrita** solo para máximo 2 términos clave.\n\n"
        f"{ctx_bloque}"
        f"MENSAJE DE {nombre_corto.upper()}: {pregunta}\n\nRESPUESTA:"
    )


def _generate_sync(prompt: str) -> str:
    """Wrapper síncrono de Gemini para usar en thread pool."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text


async def generate_response(pregunta: str, contexto: list[dict], nombre: str = "") -> dict:
    """Genera respuesta RAG con Gemini en thread pool (no bloquea event loop)."""
    fuentes = list(set(c.get("fuente", "Guía ICFES") for c in contexto if c.get("fuente")))
    prompt = _build_prompt(pregunta, contexto, nombre)

    loop = asyncio.get_event_loop()
    texto = await loop.run_in_executor(None, _generate_sync, prompt)

    return {"respuesta": texto, "fuentes": fuentes}


async def generate_response_stream(
    pregunta: str, contexto: list[dict], nombre: str = ""
) -> AsyncGenerator[str, None]:
    """Genera respuesta con Gemini en modo streaming — los chunks llegan token a token."""
    prompt = _build_prompt(pregunta, contexto, nombre)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _stream_in_thread():
        try:
            model = get_gemini_model()
            for chunk in model.generate_content(prompt, stream=True):
                # chunk.text puede lanzar ValueError en chunks de finalización sin texto
                try:
                    text = chunk.text
                    if text:
                        asyncio.run_coroutine_threadsafe(queue.put(("chunk", text)), loop)
                except (ValueError, AttributeError):
                    pass  # chunk de fin / safety — ignorar silenciosamente
        except Exception as e:
            err_msg = str(e)
            # Mensaje amigable para rate limit 429
            if "429" in err_msg or "quota" in err_msg.lower():
                friendly = "⚠️ Alcancé el límite de solicitudes de Gemini por hoy. Por favor intenta de nuevo mañana o contacta al administrador para actualizar el plan de la API."
            else:
                friendly = f"⚠️ No pude obtener respuesta ({err_msg[:80]}). Intenta de nuevo."
            asyncio.run_coroutine_threadsafe(queue.put(("error", friendly)), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(("done", None)), loop)

    t = threading.Thread(target=_stream_in_thread, daemon=True)
    t.start()

    while True:
        kind, value = await queue.get()
        if kind == "done":
            break
        elif kind == "error":
            # Yield mensaje de error en lugar de propagarlo
            yield f"\n\n*No pude obtener respuesta en este momento. Intenta de nuevo.*"
            break
        else:
            yield value
