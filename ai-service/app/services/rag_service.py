"""
Servicio RAG: orquesta embedding → búsqueda ChromaDB → generación Gemini.
RF-06, RF-07, RF-22
"""

import time
import asyncio
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.services.chroma_client import ChromaService
from app.services.gemini_client import generate_response

# Mapping nombre de programa → slug de módulo específico en ChromaDB
PROGRAMA_MODULO: dict[str, str] = {
    "Administración de Empresas":                         "administracion-de-empresas",
    "Contaduría Pública":                                 "contaduria-publica",
    "Licenciatura en Ciencias Sociales":                  "licenciatura-ciencias-sociales",
    "Ingeniería Electrónica":                             "ingenieria-electronica",
    "Ingeniería de Sistemas y Computación":               "ingenieria-de-sistemas-y-computacion",
    "Ingeniería Agronómica":                              "ingenieria-agronomica",
    "Zootecnia":                                          "zootecnia",
    "Licenciatura en Educación Física, Recreación y Deportes": "licenciatura-educacion-fisica",
}

COMPETENCIA_ESPECIFICA = "Específica"


def get_modulo(programa: str, competencia: str | None) -> str:
    """
    Determina el módulo ChromaDB a consultar:
    - Si la competencia es 'Específica' → módulo del programa (o 'general' si no está mapeado)
    - Cualquier otra competencia (Lectura Crítica, etc.) → 'general'
    """
    if competencia and competencia.strip() == COMPETENCIA_ESPECIFICA:
        return PROGRAMA_MODULO.get(programa, programa.lower().replace(" ", "-"))
    return "general"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Carga el modelo all-MiniLM-L6-v2 una sola vez — RNF-12."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def _encode_sync(pregunta: str) -> list:
    """Wrapper síncrono para correr en thread pool."""
    return get_embedding_model().encode(pregunta).tolist()


async def rag_query(pregunta: str, programa: str, competencia: str | None = None) -> dict:
    """
    Pipeline RAG completo:
    1. Genera embedding de la pregunta (en thread pool, no bloquea event loop)
    2. Busca en ChromaDB filtrado por módulo (general o específico del programa)
    3. Construye contexto con los fragmentos más relevantes
    4. Genera respuesta con Gemini Flash
    """
    start = time.time()

    # Determinar módulo según competencia
    modulo = get_modulo(programa, competencia)

    # 1. Embedding en thread pool para no bloquear el event loop
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, _encode_sync, pregunta)

    # 2. Búsqueda semántica: 2 fragmentos de ejemplos + 2 de práctica
    def query_tipo(tipo: str, n: int):
        try:
            return ChromaService.query(
                embedding=embedding,
                programa=programa,
                n_results=n,
                where_extra={"tipo": tipo},
                modulo=modulo,
            )
        except Exception:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    results_ej  = query_tipo("ejemplo",  2)
    results_pr  = query_tipo("practica", 2)

    # Combinar resultados
    def extraer(results):
        return (
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        )

    docs_ej,  metas_ej,  dists_ej  = extraer(results_ej)
    docs_pr,  metas_pr,  dists_pr  = extraer(results_pr)

    all_docs   = docs_ej  + docs_pr
    all_metas  = metas_ej + metas_pr
    all_dists  = dists_ej + dists_pr

    # 3. Filtrar por similitud aceptable
    contexto = []
    for doc, meta, dist in zip(all_docs, all_metas, all_dists):
        if dist < 0.75:
            contexto.append({
                "text":      doc,
                "tipo":      meta.get("tipo", "documento"),
                "fuente":    meta.get("fuente", "Guía ICFES"),
                "programa":  meta.get("programa", programa),
                "pagina":    meta.get("pagina"),
                "relevancia": round(1 - dist, 3),
            })

    # 4. Generación con Gemini
    result = await generate_response(pregunta=pregunta, contexto=contexto)

    tiempo_ms = int((time.time() - start) * 1000)

    return {
        **result,
        "tiempo_ms":         tiempo_ms,
        "fragmentos_usados": len(contexto),
    }
