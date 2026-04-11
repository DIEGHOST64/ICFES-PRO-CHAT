import json
import logging
import random
import hashlib
import asyncio
from typing import Any

from sentence_transformers import SentenceTransformer

from app.services.chroma_client import ChromaService
from app.services.gemini_client import get_ai_response

logger = logging.getLogger(__name__)

# Caching the embedding model globally for this process
_embedding_model: SentenceTransformer | None = None

def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def _encode_text(text: str) -> list[float]:
    model = _get_embedding_model()
    return model.encode(text).tolist()

async def mutate_and_insert_background(seeds: list[dict], competencia: str, modulo: str, programa: str):
    """
    Toma hasta 2 preguntas semillas como molde, llama a Gemini para mutarlas
    produciendo 2 versiones adicionales, y las inserta a ChromaDB.
    Las "seeds" son diccionarios procedentes de Pydantic .model_dump().
    """
    if not seeds:
        return
        
    # Tomar la semilla más robusta o al azar
    seed = random.choice(seeds)
    
    # Construir el JSON estricto de la semilla para pasarlo en el prompt
    seed_json = {
        "texto_base": seed.get("texto_base", ""),
        "enunciado": seed.get("enunciado", ""),
        "opciones": seed.get("opciones", []),
        "respuesta_correcta": seed.get("respuesta_correcta", ""),
        "explicacion": seed.get("explicacion", ""),
        "competencia": seed.get("competencia", competencia)
    }

    prompt = (
        "Eres un curador experto de preguntas ICFES.\n"
        "Abajo tienes una excelente pregunta semilla en formato JSON.\n"
        "Tu misión es crear DOS (2) variantes mutadas (clones asimétricos) basadas en esta semilla.\n"
        "Deben evaluar EXACTAMENTE LA MISMA lógica, pero cambiando el escenario, los números, los personajes o el contexto, de manera que el estudiante deba aplicar el mismo conocimiento sin memorizar el molde.\n\n"
        "FORMATO DE SALIDA (Solo JSON, sin bloques de código markdown):\n"
        "[\n"
        "  {\n"
        "    \"texto_base\": \"...\",\n"
        "    \"enunciado\": \"...\",\n"
        "    \"opciones\": [\"A. ...\", \"B. ...\", \"C. ...\", \"D. ...\"],\n"
        "    \"respuesta_correcta\": \"X. ...\",\n"
        "    \"explicacion\": \"...\",\n"
        "    \"competencia\": \"Misma de la semilla\"\n"
        "  }\n"
        "]\n\n"
        "--- SEMILLA BASE ---\n"
        f"{json.dumps(seed_json, ensure_ascii=False, indent=2)}\n"
        "--- FIN DE SEMILLA ---"
    )

    try:
        raw_response = await get_ai_response(
            prompt=prompt,
            model_name="gemini-2.5-flash",
            max_output_tokens=3000,
            temperature=0.7 # Temperatura para permitir creatividad en el escenario
        )
        
        # Parse JSON
        text = raw_response.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
                
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            logger.warning("Mutador: No se encontró arreglo JSON válido.")
            return
            
        mutations = json.loads(text[start:end + 1])
        if not isinstance(mutations, list) or len(mutations) == 0:
            return
            
    except Exception as e:
        logger.error(f"Mutador: Error llamando a Gemini o parseando JSON: {e}")
        return

    # Ingestar a ChromaDB
    collection = ChromaService.get_collection()
    if not collection:
        return
        
    loop = asyncio.get_running_loop()
    
    ids, docs, embeddings, metas = [], [], [], []
    
    for idx, item in enumerate(mutations):
        try:
            texto_b = str(item.get("texto_base", "")).strip()
            enunc = str(item.get("enunciado", "")).strip()
            opc = item.get("opciones", [])
            resp = str(item.get("respuesta_correcta", "")).strip()
            expl = str(item.get("explicacion", "")).strip()
            comp = str(item.get("competencia", competencia)).strip()
            
            if len(opc) < 4 or not enunc or not resp:
                continue
                
            doc_text = (
                f"Pregunta gen_{idx}\n"
                f"Competencia: {comp}\n"
                f"Afirmacion: \n"
                f"Contexto: {texto_b}\n"
                f"Enunciado: {enunc}\n"
                f"Opciones:\n- " + "\n- ".join(opc) + "\n"
                f"Respuesta correcta: {resp}\n"
                f"Explicacion: {expl}"
            ).strip()
            
            # Offload CPU-bound embedding generation
            embedding_vec = await loop.run_in_executor(None, _encode_text, doc_text)
            
            doc_id = hashlib.md5(f"mutated_{modulo}_{comp}_{enunc}".encode()).hexdigest()
            
            ids.append(doc_id)
            docs.append(doc_text)
            embeddings.append(embedding_vec)
            
            meta: dict[str, Any] = {
                "modulo": modulo,
                "tipo": "pregunta",
                "origen_tipo": "mutacion_ai",
                "competencia": comp,
                "fuente": f"Generación Orgánica basada en semilla ICFES (Módulo {modulo})",
                "archivo": "mutador_organico.json",
                "programa": programa,
                "pregunta_id": f"mut_ai_{idx}",
                "contexto": texto_b,
                "enunciado": enunc,
                "opciones_json": json.dumps(opc, ensure_ascii=False),
                "respuesta_correcta": resp,
                "explicacion": expl,
            }
            metas.append(meta)
            
        except Exception as e:
            logger.error(f"Mutador: Error preparando documento para Chroma: {e}")
            continue

    if ids:
        try:
            # collection.upsert might be thread safe or blocking but chroma uses requests which are fine in executors
            # wait, chromadb http client is sync, so it blocks. Let's offload the upsert too just in case.
            await loop.run_in_executor(
                None,
                lambda: collection.upsert(
                    ids=ids,
                    documents=docs,
                    embeddings=embeddings,
                    metadatas=metas,
                )
            )
            logger.info(f"🚀 Mutador: Insertadas {len(ids)} preguntas nuevas al banco para la competencia '{competencia}'.")
        except Exception as e:
            logger.error(f"Mutador: Error insertando a Chroma: {e}")
