"""
Cliente Gemini Flash para generación de respuestas RAG.
RF-07: Envía contexto recuperado y genera respuesta con fuentes.
"""

import os
import asyncio
import google.generativeai as genai
from functools import lru_cache

# Configuración de generación: limitar tokens para respuestas más rápidas
GENERATION_CONFIG = {
    "max_output_tokens": 800,
    "temperature": 0.3,
    "top_p": 0.85,
}


@lru_cache(maxsize=1)
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    return genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG)


def _build_prompt(pregunta: str, contexto: list[dict]) -> str:
    """Construye el prompt RAG diferenciando tipo de fragmento."""
    ejemplos  = [c for c in contexto if c.get("tipo") == "ejemplo"]
    practica  = [c for c in contexto if c.get("tipo") == "practica"]
    otros     = [c for c in contexto if c.get("tipo") not in ("ejemplo", "practica")]

    bloques = []

    if ejemplos:
        texto = "\n\n".join(
            f"[{i+1}] {c.get('fuente','ICFES')} | {c.get('programa','General')}\n{c['text']}"
            for i, c in enumerate(ejemplos)
        )
        bloques.append(f"CONCEPTOS Y EJEMPLOS EXPLICADOS (fuente oficial ICFES):\n{texto}")

    if practica:
        texto = "\n\n".join(
            f"[{i+1}] {c.get('fuente','ICFES')} | {c.get('programa','General')}\n{c['text']}"
            for i, c in enumerate(practica)
        )
        bloques.append(f"PREGUNTAS DE PRÁCTICA (cuadernillo oficial ICFES):\n{texto}")

    if otros:
        texto = "\n\n".join(
            f"[{i+1}] {c.get('fuente','ICFES')}\n{c['text']}"
            for i, c in enumerate(otros)
        )
        bloques.append(f"CONTEXTO ADICIONAL:\n{texto}")

    if not bloques:
        ctx_bloque = "CONTEXTO: No hay documentos indexados aún. Responde con conocimiento general sobre Saber Pro.\n\n"
    else:
        ctx_bloque = "\n\n".join(bloques) + "\n\n"

    return (
        "Eres un asistente académico de las pruebas Saber Pro (Colombia, UCundinamarca). "
        "Responde de forma clara, precisa y didáctica basándote en el contexto oficial. "
        "Si hay ejemplos explicados, úsalos para ilustrar. "
        "Si hay preguntas de práctica, puedes citarlas como ejercicio. "
        "Si no hay contexto suficiente, da consejos generales de preparación.\n\n"
        f"{ctx_bloque}"
        f"PREGUNTA: {pregunta}\n\nRESPUESTA:"
    )


def _generate_sync(prompt: str) -> str:
    """Wrapper síncrono de Gemini para usar en thread pool."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text


async def generate_response(pregunta: str, contexto: list[dict]) -> dict:
    """Genera respuesta RAG con Gemini en thread pool (no bloquea event loop)."""
    fuentes = list(set(c.get("fuente", "Guía ICFES") for c in contexto if c.get("fuente")))
    prompt = _build_prompt(pregunta, contexto)

    loop = asyncio.get_event_loop()
    texto = await loop.run_in_executor(None, _generate_sync, prompt)

    return {"respuesta": texto, "fuentes": fuentes}
