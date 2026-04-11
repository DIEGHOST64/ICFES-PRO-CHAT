import re
import os

path = "c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/app/routes/sugerencias.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add BackgroundTasks
text = text.replace('from fastapi import APIRouter, Query as QueryParam', 'from fastapi import APIRouter, Query as QueryParam, BackgroundTasks')

# 2. Helper functions
ai_functions = """
def _almacenar_preguntas_db(collection, preguntas: list[Pregunta], modulo: str):
    import time
    if not preguntas:
        return
    docs = []
    metas = []
    ids = []
    timestamp = int(time.time() * 1000)
    for i, p in enumerate(preguntas):
        docs.append(p.json())
        metas.append({
            "modulo": modulo,
            "tipo": "pregunta_generada",
            "competencia": p.competencia or "",
            "programa": p.programa or "",
            "tipo_ingles": p.tipo_ingles or "",
            "nivel_cefr": p.nivel_cefr or "",
            "nivel_dificultad": p.nivel_dificultad or ""
        })
        ids.append(f"gen_ai_{timestamp}_{i}")
    try:
        collection.add(documents=docs, metadatas=metas, ids=ids)
        print(f"[{modulo}] ALMACENADAS {len(preguntas)} preguntas en ChromaDB (tipo: pregunta_generada)")
    except Exception as e:
        print(f"[!] Error guardando preguntas AI en ChromaDB: {e}")

def _get_ai_bank_questions(collection, modulo: str, competencia: str | None, entrenamiento_general: bool, cantidad: int, is_english: bool) -> list[Pregunta]:
    docs_q, metas_q, ids_q = _get_docs_for_modulo(
        collection,
        modulo,
        "pregunta_generada",
        None if entrenamiento_general else competencia,
    )
    if not docs_q:
        return []

    import random
    import json
    triples = list(zip(docs_q, metas_q, ids_q))
    random.shuffle(triples)

    bank = []
    for doc, meta, doc_id in triples:
        try:
            parsed = json.loads(doc)
            pregunta = Pregunta(**parsed)
            is_escrita = "escrita" in (pregunta.competencia or "").lower()
            if is_escrita:
                if len(pregunta.opciones) > 0:
                    continue
            else:
                if len(pregunta.opciones) < 4:
                    continue
                if not pregunta.respuesta_correcta:
                    continue
            bank.append(pregunta)
        except Exception:
            continue

    bank = _dedupe_preguntas_by_enunciado(bank, by_competencia=entrenamiento_general)
    if not bank:
        return []

    if entrenamiento_general:
        return _select_general_mix_from_bank(bank, cantidad)

    if is_english:
        bank = _balance_english_levels([p.dict() for p in bank], cantidad, None)
        bank = _balance_english_questions(bank, cantidad)
        return [Pregunta(**b) for b in bank][:cantidad]

    return bank[:cantidad]

"""

marker = "def _get_curated_bank_questions"
text = text.replace(marker, ai_functions + "\n" + marker)

# 3. New definitions
route_def = """@router.get("", response_model=list[Pregunta])
async def sugerencias(
    background_tasks: BackgroundTasks,
    programa: str = QueryParam("General", description="Programa académico del estudiante"),
    competencia: str | None = QueryParam(None, description="Competencia (opcional)"),
    nivel_objetivo: str | None = QueryParam(None, description="Nivel objetivo para Inglés: A2 o B1"),
    dificultad_objetivo: str | None = QueryParam(None, description="Dificultad objetivo para competencias generales: basico/intermedio/avanzado"),
    cantidad: int = QueryParam(15, ge=5, le=30, description="Número de preguntas del entrenamiento"),
):"""

miner_def = """async def _background_question_miner(
    programa: str,
    competencia: str | None,
    nivel_objetivo: str | None,
    dificultad_objetivo: str | None,
    cantidad: int,
    entrenamiento_general: bool,
    modulo: str,
    is_english: bool,
    comp_meta: str
):
    import time
    print(f"[*] INICIANDO background miner para {modulo} - {comp_meta} (Meta original: {cantidad} preguntas)...")
    # Generar MAS preguntas en background para llenar agresivamente el banco
    cantidad_bg = max(cantidad, 30)
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return\n"""

# Splits
old_route_def_start = '@router.get("", response_model=list[Pregunta])'
sugerencias_idx = text.find(old_route_def_start)
body_start_idx = text.find("    collection = ChromaService.get_collection()", sugerencias_idx)

new_sugerencias_body = """
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return []

    competencia_clean = (competencia or "").strip()
    entrenamiento_general = competencia is None or competencia_clean == "" or competencia_clean.lower() in ("todas", "todos", "general")
    cantidad = max(5, min(cantidad, 30))
    if "escrita" in competencia_clean.lower():
        cantidad = 1

    cache_key = _build_sugerencias_cache_key(
        programa=programa,
        competencia=competencia,
        nivel_objetivo=nivel_objetivo,
        dificultad_objetivo=dificultad_objetivo,
        cantidad=cantidad,
    )
    cached = _get_cached_sugerencias(cache_key, cantidad)
    if cached is not None:
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, get_modulo(programa, None if entrenamiento_general else competencia),
            _is_english_competencia(competencia), competencia or "General"
        )
        return cached

    modulo = get_modulo(programa, None if entrenamiento_general else competencia)
    is_english = _is_english_competencia(competencia)

    ai_bank = _get_ai_bank_questions(collection, modulo, competencia, entrenamiento_general, cantidad, is_english)
    
    if len(ai_bank) >= cantidad:
        ai_bank = ai_bank[:cantidad]
        _set_cached_sugerencias(cache_key, ai_bank)
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, modulo, is_english, competencia or "General"
        )
        return ai_bank

    preguntas_curadas = _get_curated_bank_questions(collection, modulo, programa, competencia, entrenamiento_general, cantidad)
    combined = _merge_seed_with_generated(ai_bank, preguntas_curadas, cantidad, entrenamiento_general)
    
    if len(combined) >= cantidad:
        _set_cached_sugerencias(cache_key, combined)
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, modulo, is_english, competencia or "General"
        )
        return combined

    # FALLBACK EXTREMO para carga inicial
    docs_pr, _, _ = _get_docs_for_modulo(collection, modulo, "practica", None if entrenamiento_general else competencia)
    if docs_pr:
        fallback_pool = _build_deterministic_fallback_questions(docs_pr, cantidad, competencia or "General", is_english, dificultad_objetivo)
        fallback_preguntas = []
        for item in fallback_pool:
            try:
                import time
                fallback_preguntas.append(Pregunta(
                    id=f"fb_{int(time.time())}",
                    texto_base=str(item.get("texto_base","")),
                    enunciado=str(item.get("enunciado","")),
                    opciones=item.get("opciones",[]),
                    respuesta_correcta=str(item.get("respuesta_correcta","")),
                    explicacion=str(item.get("explicacion","")),
                    competencia=str(item.get("competencia", competencia or "General")),
                    programa=programa,
                    tipo_ingles=str(item.get("tipo_ingles","")) if is_english else None,
                    nivel_cefr=str(item.get("nivel_cefr","")) if is_english else None,
                    nivel_dificultad=str(item.get("nivel_dificultad","")) if not is_english else None
                ))
            except Exception: pass
        combined = _merge_seed_with_generated(combined, fallback_preguntas, cantidad, entrenamiento_general)
    
    if combined:
        _set_cached_sugerencias(cache_key, combined)
    
    background_tasks.add_task(
        _background_question_miner,
        programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
        entrenamiento_general, modulo, is_english, competencia or "General"
    )
    return combined

"""

miner_body_start_str = "docs_pr, metas_pr, ids_pr = _get_docs_for_modulo("
miner_body_start_idx = text.find(miner_body_start_str, body_start_idx)
route_end_idx = text.find('@router.post("/apoyo-pregunta")')

miner_body_raw = text[miner_body_start_idx:route_end_idx]

# IMPORTANT: we must change `cantidad` inside miner_body_raw to `cantidad_bg` because we want the miner to aggressively generate 30+ questions at a time.
miner_body_raw = miner_body_raw.replace("cantidad", "cantidad_bg")
miner_body_raw = miner_body_raw.replace("return combined", "")
miner_body_raw = miner_body_raw.replace("    return preguntas", "    _almacenar_preguntas_db(collection, preguntas, modulo)")

# Indent miner body
miner_body_fixed = "\n".join(["    " + line for line in miner_body_raw.split("\n")])

new_file_content = (
    text[:sugerencias_idx] +
    miner_def + miner_body_fixed + "\n\n" +
    route_def + new_sugerencias_body + "\n" +
    text[route_end_idx:]
)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_file_content)

print("Refactorizado con exito! (v2)")
