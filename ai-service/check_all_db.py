import sys
sys.path.append('.')
from app.services.chroma_client import ChromaService

ChromaService.initialize()
col = ChromaService.get_collection()

competencias = [
    "Lectura Crítica",
    "Razonamiento Cuantitativo",
    "Ciudadanas",
    "Comunicación Escrita",
    "Inglés",
]

print(f"Total documentos en DB: {col.count()}\n")

for comp in competencias:
    res = col.get(where={"competencia": comp}, include=["metadatas"])
    generadas = len([m for m in res["metadatas"] if m.get("tipo") == "pregunta_generada"])
    otras = len(res["metadatas"]) - generadas
    print(f"  {comp:30s} | Generadas AI: {generadas:4d} | Otras: {otras:4d}")
