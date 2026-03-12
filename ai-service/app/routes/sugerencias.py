"""
RF-09, RF-23: Endpoint GET /sugerencias — Preguntas de práctica
Devuelve preguntas aleatorias filtradas por módulo (general o específico del programa).
Usa Gemini para generar preguntas estructuradas desde fragmentos del cuadernillo ICFES.
"""

import json
import random
import asyncio
from fastapi import APIRouter, Query as QueryParam
from pydantic import BaseModel

from app.services.chroma_client import ChromaService
from app.services.rag_service import get_modulo
from app.services.gemini_client import get_gemini_quiz_model

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


def _generate_questions_sync(fragments: list[str], cantidad: int,
                             competencia: str | None, programa: str) -> list[dict]:
    """
    Llama a Gemini para generar preguntas de selección múltiple
    basadas en fragmentos reales del cuadernillo ICFES.
    """
    context = "\n\n---\n\n".join(fragments[:5])
    comp_label = competencia or "Competencias Genéricas Saber Pro"
    prompt = (
        f"Eres un experto en la prueba Saber Pro de Colombia (ICFES).\n"
        f"Basándote EXCLUSIVAMENTE en los siguientes fragmentos del cuadernillo oficial, "
        f"genera exactamente {cantidad} preguntas de selección múltiple para un estudiante "
        f"de {programa} en la competencia de {comp_label}.\n\n"
        f"FRAGMENTOS DEL CUADERNILLO:\n{context}\n\n"
        f"REGLAS ESTRICTAS:\n"
        f"- Cada pregunta debe ser directamente respondible con los fragmentos dados.\n"
        f"- 4 opciones por pregunta (A, B, C, D). Solo UNA correcta.\n"
        f"- texto_base: copia 2-5 oraciones del fragmento original que el estudiante NECESITA "
        f"leer para poder responder la pregunta. Debe ser el contexto directo, no un resumen.\n"
        f"- La explicación debe ser corta (1-2 oraciones) y explicar POR QUÉ la opción es correcta.\n"
        f"- Devuelve ÚNICAMENTE un array JSON válido, sin markdown, sin texto extra.\n\n"
        f'Formato: [{{"texto_base":"...","enunciado":"...","opciones":["A. ...","B. ...","C. ...","D. ..."],'
        f'"respuesta_correcta":"A. ...","explicacion":"...","competencia":"{comp_label}"}}]'
    )
    model = get_gemini_quiz_model()
    response = model.generate_content(prompt)
    text = response.text.strip()
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
    return json.loads(text)


def _get_docs(collection, where: dict, limit: int = 200) -> tuple:
    """Ejecuta collection.get() y devuelve (docs, metas, ids) o tupla vacía si falla."""
    try:
        r = collection.get(where=where, include=["documents", "metadatas"], limit=limit)
        return r.get("documents", []), r.get("metadatas", []), r.get("ids", [])
    except Exception:
        return [], [], []


def _get_docs_for_modulo(collection, modulo: str, tipo: str) -> tuple:
    """
    Busca documentos con cascada de fallbacks:
    1. modulo + tipo
    2. solo tipo (por si docs viejos no tienen campo modulo)
    3. sin filtros
    """
    # Nivel 1: modulo + tipo
    docs, metas, ids = _get_docs(collection, {"$and": [{"modulo": modulo}, {"tipo": tipo}]})
    if docs:
        return docs, metas, ids

    # Nivel 2: solo tipo
    docs, metas, ids = _get_docs(collection, {"tipo": tipo})
    if docs:
        return docs, metas, ids

    # Nivel 3: sin filtros
    return _get_docs(collection, {})


def _adaptar_a_pregunta(doc: str, meta: dict, doc_id: str,
                        competencia: str | None, programa: str) -> Pregunta:
    """Convierte un fragmento (practica/ejemplo) al modelo Pregunta para el frontend."""
    opciones_raw = meta.get("opciones", "")
    opciones = [o.strip() for o in opciones_raw.split(",") if o.strip()] if opciones_raw else []
    return Pregunta(
        id=doc_id,
        enunciado=meta.get("enunciado", doc[:600]),
        opciones=opciones,
        respuesta_correcta=meta.get("respuesta_correcta", ""),
        explicacion=meta.get("explicacion", "Fragmento extraído del cuadernillo oficial ICFES."),
        competencia=meta.get("competencia", competencia or "General"),
        programa=meta.get("programa", programa),
    )


@router.get("", response_model=list[Pregunta])
async def sugerencias(
    programa: str = QueryParam(..., description="Programa académico del estudiante"),
    competencia: str | None = QueryParam(None, description="Competencia (opcional)"),
    cantidad: int = QueryParam(5, ge=1, le=20, description="Número de preguntas"),
):
    """
    Genera preguntas de práctica estructuradas usando Gemini sobre fragmentos del cuadernillo ICFES.
    1. Recupera fragmentos de ChromaDB según módulo/competencia
    2. Llama a Gemini para generar N preguntas de selección múltiple reales
    3. Devuelve lista de Pregunta con opciones, respuesta correcta y explicación
    """
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return []

    modulo = get_modulo(programa, competencia)

    # Recuperar fragmentos de contexto (practica > ejemplo > cualquier cosa)
    docs, metas, ids = _get_docs_for_modulo(collection, modulo, "practica")
    if not docs:
        docs, metas, ids = _get_docs_for_modulo(collection, modulo, "ejemplo")
    if not docs:
        return []

    # Seleccionar fragmentos aleatorios variados para que Gemini tenga contexto rico
    sample_size = min(len(docs), max(cantidad * 2, 6))
    indices = random.sample(range(len(docs)), sample_size)
    fragments = [docs[i] for i in indices]
    comp_meta = metas[indices[0]].get("competencia", competencia or "General") if metas else (competencia or "General")

    # Generar preguntas con Gemini en thread pool
    loop = asyncio.get_event_loop()
    try:
        raw = await loop.run_in_executor(
            None, _generate_questions_sync, fragments, cantidad, competencia, programa
        )
    except Exception as e:
        # Si Gemini falla o el JSON no es válido, devolver vacío
        return []

    preguntas = []
    for i, item in enumerate(raw[:cantidad]):
        try:
            preguntas.append(Pregunta(
                id=f"gen_{i}_{modulo}",
                texto_base=item.get("texto_base", ""),
                enunciado=item.get("enunciado", ""),
                opciones=item.get("opciones", []),
                respuesta_correcta=item.get("respuesta_correcta", ""),
                explicacion=item.get("explicacion", ""),
                competencia=item.get("competencia", comp_meta),
                programa=programa,
            ))
        except Exception:
            continue

    return preguntas

