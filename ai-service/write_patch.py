import sys, re
path = 'c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/app/routes/sugerencias.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: IndexError in respuesta_correcta for Escrita
old_resp = r"""
            respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
            if respuesta_correcta not in opciones:
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                respuesta_correcta = matched or opciones[0]
"""

new_resp = r"""
            respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
            if not is_escr and respuesta_correcta not in opciones:
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                respuesta_correcta = matched or (opciones[0] if opciones else "")
"""

text = re.sub(old_resp.strip().replace("(", r"\(").replace(")", r"\)").replace("[", r"\[").replace("]", r"\]").replace(".", r"\.").replace("*", r"\*").replace("^", r"\^"), new_resp.strip(), text, flags=re.MULTILINE)

# We will just write a custom replacer script rather than complex regex
with open('c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/patcher.py', 'w', encoding='utf-8') as f:
    f.write(r'''
import sys
path = 'app/routes/sugerencias.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix respuesta_correcta
text = text.replace(
"""            respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
            if respuesta_correcta not in opciones:
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                respuesta_correcta = matched or opciones[0]""",
"""            respuesta_correcta = _repair_text_encoding(str(item.get("respuesta_correcta", ""))).strip()
            is_escrita_flag = "escrita" in (str(item.get("competencia", "")) or "General").lower()
            if not is_escrita_flag and respuesta_correcta not in opciones:
                normalized_correct = re.sub(r"^[A-Da-d]\.\s*", "", respuesta_correcta).strip().lower()
                matched = next((opt for opt in opciones if normalized_correct and normalized_correct in re.sub(r"^[A-Da-d]\.\s*", "", opt).strip().lower()), None)
                respuesta_correcta = matched or (opciones[0] if opciones else "")"""
)

# Fix texto_base for English part 1,2,3
text = text.replace(
"""            raw_tb = str(item.get("texto_base", ""))
            if is_item_cloze:
                texto_base = _normalize_text_base_quality(raw_tb, min_words=10)
                if not texto_base:
                    texto_base = raw_tb.strip()  # Preservar original para cloze
            else:
                texto_base = _normalize_text_base_quality(raw_tb)
            if not texto_base:
                continue""",
"""            raw_tb = str(item.get("texto_base", ""))
            if is_item_cloze:
                texto_base = _normalize_text_base_quality(raw_tb, min_words=10)
                if not texto_base:
                    texto_base = raw_tb.strip()  # Preservar original para cloze
            elif item_tipo_ingles in ("part1", "part2", "part3"):
                texto_base = raw_tb.strip() # Parts 1, 2, 3 have very short or empty text_base!
            else:
                texto_base = _normalize_text_base_quality(raw_tb)
                
            if not texto_base and item_tipo_ingles != "part3": # Part 3 is expected to be empty
                continue"""
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Patch aplicado con exito!")
''')
