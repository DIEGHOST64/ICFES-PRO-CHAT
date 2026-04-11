import sys
sys.path.append('.')
from app.services.chroma_client import ChromaService

ChromaService.initialize()
col = ChromaService.get_collection()

# English
res_eng = col.get(where={"competencia": "Inglés"}, include=["metadatas"])
total_eng = len([m for m in res_eng["metadatas"] if m.get("tipo") == "pregunta_generada"])

print(f"Total English AI Generated: {total_eng}")
if total_eng > 0:
    sample = next(m for m in res_eng["metadatas"] if m.get("tipo") == "pregunta_generada")
    print(f"Sample Eng Meta: {sample}")

# Escrita
res_esc = col.get(where={"competencia": "Comunicación Escrita"}, include=["metadatas"])
total_esc = len([m for m in res_esc["metadatas"] if m.get("tipo") == "pregunta_generada"])

print(f"Total Escrita AI Generated: {total_esc}")
if total_esc > 0:
    sample = next(m for m in res_esc["metadatas"] if m.get("tipo") == "pregunta_generada")
    print(f"Sample Escrita Meta: {sample}")
