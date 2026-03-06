"""
RF-09, RF-23: Endpoint GET /sugerencias — Preguntas de práctica
Devuelve preguntas aleatorias filtradas por módulo (general o específico del programa).

Routing:
  - competencia != "Específica"  →  modulo = "general"
  - competencia == "Específica"  →  modulo = slug del programa
"""

import random
from fastapi import APIRouter, Query as QueryParam
from pydantic import BaseModel

from app.services.chroma_client import ChromaService
from app.services.rag_service import get_modulo

router = APIRouter()


class Pregunta(BaseModel):
    id: str
    enunciado: str
    opciones: list[str]
    respuesta_correcta: str
    explicacion: str
    competencia: str
    programa: str


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
    Devuelve fragmentos de práctica desde ChromaDB.
    Routing automático:
      - Módulos comunes (Lectura Crítica, etc.)  →  busca en modulo='general'
      - Módulo Específico                         →  busca en modulo=<slug del programa>
    Prioridad: banco JSON estructurado (tipo=pregunta) → practica PDF → ejemplo PDF
    """
    collection = ChromaService.get_collection()

    if collection.count() == 0:
        return []

    # Determinar módulo basándose en la competencia
    modulo = get_modulo(programa, competencia)

    # Prioridad 1: banco JSON con preguntas estructuradas
    docs, metas, ids = _get_docs_for_modulo(collection, modulo, "pregunta")

    # Prioridad 2: fragmentos del cuadernillo de práctica
    if not docs:
        docs, metas, ids = _get_docs_for_modulo(collection, modulo, "practica")

    # Prioridad 3: fragmentos de ejemplos explicados
    if not docs:
        docs, metas, ids = _get_docs_for_modulo(collection, modulo, "ejemplo")

    if not docs:
        return []

    indices = random.sample(range(len(docs)), min(cantidad, len(docs)))

    return [
        _adaptar_a_pregunta(
            docs[i],
            metas[i] if i < len(metas) else {},
            ids[i] if i < len(ids) else str(i),
            competencia,
            programa,
        )
        for i in indices
    ]

