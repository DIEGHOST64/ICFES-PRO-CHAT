import re

file_path = "c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/app/routes/sugerencias.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []

# Replace background import
for line in lines:
    if line.startswith("from fastapi import APIRouter, Query as QueryParam"):
        new_lines.append("from fastapi import APIRouter, Query as QueryParam, BackgroundTasks\n")
    else:
        new_lines.append(line)

lines = new_lines

# Extract sugerencias block
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("@router.get(\"\", response_model=list[Pregunta])"):
        start_idx = i
    if line.startswith("@router.post(\"/apoyo-pregunta\")"):
        end_idx = i
        break

pre_route = lines[:start_idx]
post_route = lines[end_idx:]

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
        from app.routes.sugerencias import _balance_english_levels, _balance_english_questions
        bank = _balance_english_levels([p.dict() for p in bank], cantidad, None)
        bank = _balance_english_questions(bank, cantidad)
        return [Pregunta(**b) for b in bank][:cantidad]

    return bank[:cantidad]

"""

sugerencias_logic = lines[start_idx:end_idx]

# Remove the old function boundary
route_sig_end = -1
for i, l in enumerate(sugerencias_logic):
    if l.strip() == "):":
        route_sig_end = i
        break

# The body of sugerencias
body_lines = sugerencias_logic[route_sig_end+1:]

# We need to split body_lines at "    docs_pr, metas_pr, ids_pr = _get_docs_for_modulo("
split_idx = -1
for i, l in enumerate(body_lines):
    if l.startswith("    docs_pr, metas_pr, ids_pr = _get_docs_for_modulo("):
        split_idx = i
        break

fast_load = body_lines[:split_idx]
slow_miner = body_lines[split_idx:]

new_route_method = """@router.get("", response_model=list[Pregunta])
async def sugerencias(
    background_tasks: BackgroundTasks,
    programa: str = QueryParam("General", description="Programa académico del estudiante"),
    competencia: str | None = QueryParam(None, description="Competencia (opcional)"),
    nivel_objetivo: str | None = QueryParam(None, description="Nivel objetivo para Inglés: A2 o B1"),
    dificultad_objetivo: str | None = QueryParam(None, description="Dificultad objetivo para competencias generales: basico/intermedio/avanzado"),
    cantidad: int = QueryParam(15, ge=5, le=30, description="Número de preguntas del entrenamiento"),
):
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
            _is_english_competencia(competencia), competencia or "General", cache_key
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
            entrenamiento_general, modulo, is_english, competencia or "General", cache_key
        )
        return ai_bank

    preguntas_curadas = _get_curated_bank_questions(collection, modulo, programa, competencia, entrenamiento_general, cantidad)
    combined = _merge_seed_with_generated(ai_bank, preguntas_curadas, cantidad, entrenamiento_general)
    
    if len(combined) >= cantidad:
        _set_cached_sugerencias(cache_key, combined)
        background_tasks.add_task(
            _background_question_miner,
            programa, competencia, nivel_objetivo, dificultad_objetivo, cantidad,
            entrenamiento_general, modulo, is_english, competencia or "General", cache_key
        )
        return combined

    docs_pr, _, _ = _get_docs_for_modulo(collection, modulo, "practica", None if entrenamiento_general else competencia)
    if docs_pr:
        fallback_pool = _build_deterministic_fallback_questions(docs_pr, cantidad, competencia or "General", is_english, dificultad_objetivo)
        fallback_preguntas = []
        for item in fallback_pool:
            try:
                import time
                fallback_preguntas.append(Pregunta(
                    id=f"fb_{int(time.time())}_{len(fallback_preguntas)}",
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
        entrenamiento_general, modulo, is_english, competencia or "General", cache_key
    )
    return combined

"""

miner_header = """async def _background_question_miner(
    programa: str, competencia: str | None, nivel_objetivo: str | None,
    dificultad_objetivo: str | None, cantidad: int, entrenamiento_general: bool,
    modulo: str, is_english: bool, comp_meta: str, cache_key: str
):
    print(f"[*] INICIANDO background miner para {modulo} - {comp_meta} (Meta: {cantidad} preguntas)...")
    cantidad_bg = max(cantidad, 45) # Oversample
    # Evito reescribir variables abajo.
    cantidad = cantidad_bg
    collection = ChromaService.get_collection()
    if collection.count() == 0:
        return
    preguntas_seed = [] # Reemplaza el seed q faltaba
"""

new_slow_miner_lines = []
for line in slow_miner:
    if line.strip().startswith("return"):
        # Instead of returning questions, we store them. Also remove return []
        if "return []" in line:
            new_slow_miner_lines.append("    return\n")
        elif "return combined" in line or "return preguntas" in line:
            pass # We replace it below
        else:
            new_slow_miner_lines.append(line)
    elif "if len(preguntas) < cantidad and docs and not entrenamiento_general:" in line:
        new_slow_miner_lines.append(line)
    else:
        new_slow_miner_lines.append(line)

# Add storing at the end of miner
new_slow_miner_lines.append("    if combined:\n")
new_slow_miner_lines.append("        _almacenar_preguntas_db(collection, combined, modulo)\n")
new_slow_miner_lines.append("    elif 'preguntas' in locals() and preguntas:\n")
new_slow_miner_lines.append("        _almacenar_preguntas_db(collection, preguntas, modulo)\n")


final_lines = pre_route + [ai_functions] + [miner_header] + new_slow_miner_lines + ["\n\n"] + [new_route_method] + post_route

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(final_lines)

print("Refactorizado con exito v3!")
