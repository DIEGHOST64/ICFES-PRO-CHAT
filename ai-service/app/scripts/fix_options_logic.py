import sys
import re

file_path = "c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/app/routes/sugerencias.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix 1: _merge_seed_with_generated
old_1 = """        if len(p.opciones) < 4:
            continue"""
new_1 = """        is_escrita_item = "escrita" in (p.competencia or "").lower()
        is_ingles_item = "ingl" in (p.competencia or "").lower()
        if is_escrita_item:
            if len(p.opciones) > 0: continue
        elif is_ingles_item:
            if len(p.opciones) < 3: continue
        else:
            if len(p.opciones) < 4: continue"""
text = text.replace(old_1, new_1)

# Fix 2: _get_curated_bank_questions (It already drops English explicitly before this, so we leave it alone, but just in case we let it be)
# Oh wait, English is explicitly dropped with `if is_ingles_q: continue`. So len(pregunta.opciones) < 4 there only applies to general.

# Fix 3: _get_ai_bank_questions
old_3 = """            is_escrita = "escrita" in (pregunta.competencia or "").lower()
            if is_escrita:
                if len(pregunta.opciones) > 0:
                    continue
            else:
                if len(pregunta.opciones) < 4:
                    continue
                if not pregunta.respuesta_correcta:
                    continue"""
new_3 = """            is_escrita = "escrita" in (pregunta.competencia or "").lower()
            is_ingles = "ingl" in (pregunta.competencia or "").lower()
            if is_escrita:
                if len(pregunta.opciones) > 0:
                    continue
            elif is_ingles:
                if len(pregunta.opciones) < 3:
                    continue
                if not pregunta.respuesta_correcta:
                    continue
            else:
                if len(pregunta.opciones) < 4:
                    continue
                if not pregunta.respuesta_correcta:
                    continue"""
text = text.replace(old_3, new_3)

# Fix 4: The 4 blocks in _background_question_miner
def replace_miner_opciones(text, comp_var):
    old_block = f"""                    opciones = _coerce_options(item.get("opciones", []))
                    if len(opciones) < 4:
                        continue
                    opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                    if any(_is_placeholder_option(opt) for opt in opciones):
                        continue"""
    new_block = f"""                    opciones = _coerce_options(item.get("opciones", []))
                    is_escr = "escrita" in ({comp_var} or "General").lower()
                    is_ingl = "ingl" in ({comp_var} or "General").lower()
                    if is_escr:
                        if len(opciones) > 0: continue
                    elif is_ingl:
                        if len(opciones) < 3: continue
                        opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]
                        if any(_is_placeholder_option(opt) for opt in opciones): continue
                    else:
                        if len(opciones) < 4: continue
                        opciones = [_clean_option_text(opciones[j], j) for j in range(4)]
                        if any(_is_placeholder_option(opt) for opt in opciones): continue"""
    return text.replace(old_block, new_block)

text = replace_miner_opciones(text, "comp_name")
text = replace_miner_opciones(text, "competencia")
text = replace_miner_opciones(text, "item_comp")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Reemplazos realizados!")
