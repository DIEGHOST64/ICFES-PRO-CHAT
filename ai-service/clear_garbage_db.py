import sys
import os
from pathlib import Path

# Fix python path
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))

from app.services.chroma_client import ChromaService

def clear_garbage():
    print("Iniciando limpieza de base de datos...")
    ChromaService.initialize()
    col = ChromaService.get_collection()
    
    comp = "Razonamiento Cuantitativo"
    
    try:
        res = col.get(where={"competencia": comp}, include=["metadatas"])
        if not res or not res.get("ids"):
            print("No se encontraron registros de", comp)
            return

        ids_to_delete = []
        for i, meta in enumerate(res.get("metadatas", [])):
            if meta:
                origen_tipo = meta.get("origen_tipo")
                tipo = meta.get("tipo")
                if tipo in ["pregunta_generada", "mutacion_ai", "mutacion"]:
                    ids_to_delete.append(res["ids"][i])
                elif origen_tipo in ["generacion_ai", "mutacion_ai"]:
                    ids_to_delete.append(res["ids"][i])

        # Deduplicate
        ids_to_delete = list(set(ids_to_delete))

        if ids_to_delete:
            print(f"Borrando {len(ids_to_delete)} preguntas basura de {comp}...")
            # Delete in small batches if chroma complains, usually fine 
            batch_size = 500
            for k in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[k:k+batch_size]
                col.delete(ids=batch)
                print(f"Borrado lote de {len(batch)} items.")
            print("Limpieza terminada con éxito.")
        else:
            print(f"No hay preguntas clasificadas como generadas en {comp}.")
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    clear_garbage()
