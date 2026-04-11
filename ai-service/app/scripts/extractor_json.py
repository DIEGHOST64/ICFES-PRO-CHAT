import os
import argparse
import json
import re
import asyncio
from pathlib import Path
from tqdm import tqdm
import warnings

# Suprimir advertencias de grpc/pymupdf
warnings.filterwarnings("ignore")

import google.generativeai as genai

# ── Configuración ────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY no encontrada en variables de entorno.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
# Como la tarea es extraer texto real del PDF (ETL) no necesitamos gran temperatura.
config_extractor = {
    "temperature": 0.0,
    "top_p": 0.9,
}
model = genai.GenerativeModel("gemini-2.5-flash", generation_config=config_extractor)


def fix_encoding(text: str) -> str:
    try:
        fixed = text.encode("cp1252", errors="replace").decode("utf-8", errors="replace")
        def _ruido(t):
            return sum(1 for c in t if c in "Ã\x83\xc3\xc2\ufffd")
        return fixed if _ruido(fixed) < _ruido(text) else text
    except Exception:
        return text

def parse_json_from_llm(output: str) -> list[dict]:
    raw = output.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(raw[start:end + 1])
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"    [!] Error al parsear JSON devuelto por Gemini: {e}")
    return []

async def extract_questions_from_text(texto: str, file_name: str) -> list[dict]:
    """Usa Gemini para raspar preguntas atómicas del texto en bruto de un PDF."""
    if len(texto.strip()) < 100:
        return []

    prompt = (
        "Eres un curador experto en exámenes tipo ICFES/Saber Pro.\n"
        "Abajo te paso un bloque de texto escaneado de un cuadernillo oficial de pruebas ICFES.\n"
        "Tu misión es encontrar, reconstruir y estructurar CUALQUIER pregunta académica que aparezca.\n\n"
        "INSTRUCCIONES EXTRA ESTRICTAS:\n"
        "- Muchas veces el texto dirá 'Responda las preguntas 1 y 2 de acuerdo con la siguiente información...', ese es tu *texto_base* o *contexto*, debes adjuntarlo a cada pregunta que siga (A la 1 y a la 2 por igual).\n"
        "- Ignora señales administrativas como 'hoja de respuestas', firmas, director general, etc.\n"
        "- Extrae o deduce la respuesta correcta si el cuadernillo menciona 'Clave de respuesta: X' o 'Justificación de la respuesta'. "
        "Si no está indicada la respuesta correcta en este bloque y de verdad es imposible saberla (incluso solucionándolo tú lógicamente), deduce la correcta mediante tu conocimiento para entregar una pregunta validada.\n"
        "- En 'explicacion' incluye un breve razonamiento de porqué la correcta lo es.\n"
        "- Las opciones DEBEN empezar con letra y punto. Ej: 'A. Opción alfa', 'B. Opción beta'. Mínimo 4 opciones por pregunta.\n\n"
        "FORMATO DE SALIDA:\n"
        "Devuelve EXCLUSIVAMENTE un arreglo JSON con esta estructura (nada de Markdown fuera del JSON):\n"
        "[\n"
        "  {\n"
        "    \"contenido\": {\n"
        "      \"contexto\": \"Texto de lectura previo, o tabla en formato texto explicada.\",\n"
        "      \"enunciado\": \"La pregunta en sí...\",\n"
        "      \"opciones\": [\"A. ...\", \"B. ...\", \"C. ...\", \"D. ...\"]\n"
        "    },\n"
        "    \"solucion\": {\n"
        "      \"correcta\": \"A\",\n"
        "      \"justificacion_tecnica\": \"Breve explicación del porqué...\"\n"
        "    },\n"
        "    \"metadatos\": {\n"
        "      \"competencia\": \"\",\n"
        "      \"fuente\": \"" + file_name + "\"\n"
        "    }\n"
        "  }\n"
        "]\n\n"
        "--- INICIO DEL TEXTO DEL CUADERNILLO ---\n"
        f"{texto[:9000]}\n"
        "--- FIN DEL TEXTO ---"
    )
    
    loop = asyncio.get_event_loop()
    try:
        respuesta = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        text_out = respuesta.text
        return parse_json_from_llm(text_out)
    except Exception as e:
        print(f"    [!] Error en llamada a Gemini: {e}")
        return []

async def process_pdf(pdf_path: Path):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[!] PyMuPDF no está instalado. `pip install pymupdf`")
        return []
    
    print(f"\n=> Analizando PDF: {pdf_path.name}")
    doc = fitz.open(str(pdf_path))
    all_questions = []
    
    # Procesaremos por grupos de 2 o 3 páginas para darle contexto amplio al modelo
    # pero sin sobrepasar el límite de tokens ni mezclar demasiadas preguntas.
    step = 2 
    total_pages = doc.page_count
    
    for i in range(0, total_pages, step):
        bloque = []
        for j in range(i, min(i+step, total_pages)):
            pagina_texto = fix_encoding(doc[j].get_text())
            bloque.append(pagina_texto)
            
        texto_unido = "\n".join(bloque)
        
        # Saltarse bloques que son obvias introducciones (portadas cortas)
        if len(texto_unido.split()) < 40:
            continue
            
        print(f"  -> Extrayendo lote de páginas p.{i+1}-p.{min(i+step, total_pages)} ...", end="", flush=True)
        questions = await extract_questions_from_text(texto_unido, pdf_path.name)
        
        if questions:
            print(f" OK (Encontradas {len(questions)} preguntas)")
            all_questions.extend(questions)
        else:
            print(f" Cero preguntas viables obtenidas.")
            
        # Respiro para no saturar Rate Limits rápidos
        await asyncio.sleep(2)
        
    doc.close()
    return all_questions

async def async_main(directory: Path):
    pdfs = list(directory.rglob("*.pdf"))
    if not pdfs:
        print("No se encontraron PDFs en el directorio especificado.")
        return
        
    print(f"Se encontraron {len(pdfs)} PDFs para extraer en '{directory}'.\n")
    
    for pdf_path in pdfs:
        # Generar metadata nombre output
        out_json_name = pdf_path.stem + "_extraidas.json"
        out_json_path = pdf_path.parent / out_json_name
        
        if out_json_path.exists():
            print(f"[-] Saltando '{pdf_path.name}' — Ya existe el banco extraído ({out_json_name})")
            continue
            
        banco = await process_pdf(pdf_path)
        
        if banco:
            # Envelop de la colección
            payload = {
                "origen": str(pdf_path.name),
                "total_preguntas": len(banco),
                "preguntas": banco
            }
            with open(out_json_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f" [✓] Guardado en '{out_json_name}' ({len(banco)} prgts)")
        else:
            print(f" [✕] No se guardó '{out_json_name}', extracción vacía.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer banco JSON a partir de PDFs de Cuadernillos ICFES usando Gemini")
    parser.add_argument("--dir", type=str, default="data/icfes_docs", help="Directorio raíz para buscar PDFs")
    args = parser.parse_args()
    
    asyncio.run(async_main(Path(args.dir)))
