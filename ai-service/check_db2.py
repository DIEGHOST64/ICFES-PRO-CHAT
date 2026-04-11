import sys, re
path = 'c:/Users/DIEGHOST/ICFES-PRO-CHAT/ai-service/app/routes/sugerencias.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

pattern = re.compile(
    r'(?P<indent>[ \t]+)opciones = _coerce_options\(item\.get\(\"opciones\", \[\]\)\)\n'
    r'[ \t]+if len\(opciones\) < 4:\n'
    r'[ \t]+continue\n'
    r'[ \t]+opciones = \[\_clean_option_text\(opciones\[j\], j\) for j in range\(4\)\]\n'
    r'[ \t]+if any\(\_is_placeholder_option\(opt\) for opt in opciones\):\n'
    r'[ \t]+continue'
)

def replacer(match):
    indent = match.group('indent')
    return (
        f'{indent}opciones = _coerce_options(item.get("opciones", []))\n'
        f'{indent}is_escr = "escrita" in (item_comp or "General").lower()\n'
        f'{indent}is_ingl = "ingl" in (item_comp or "General").lower()\n'
        f'{indent}if is_escr:\n'
        f'{indent}    if len(opciones) > 0: continue\n'
        f'{indent}elif is_ingl:\n'
        f'{indent}    if len(opciones) < 3: continue\n'
        f'{indent}    opciones = [_clean_option_text(opciones[j], j) for j in range(len(opciones))]\n'
        f'{indent}    if any(_is_placeholder_option(opt) for opt in opciones): continue\n'
        f'{indent}else:\n'
        f'{indent}    if len(opciones) < 4: continue\n'
        f'{indent}    opciones = [_clean_option_text(opciones[j], j) for j in range(4)]\n'
        f'{indent}    if any(_is_placeholder_option(opt) for opt in opciones): continue'
    )

new_text, count = pattern.subn(replacer, text)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_text)

print(f'Reemplazados bloques exactos: {count}')
