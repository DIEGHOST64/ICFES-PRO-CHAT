import os
import sys
import asyncio
from pathlib import Path

# Añadir el raíz del servicio para poder importar módulos
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from app.services.chroma_client import ChromaService
from app.routes.sugerencias import _background_question_miner, get_modulo

async def sembrar_banco(programa: str, num_ciclos: int = 5):
    print("=======================================")
    print(f"[{programa}] INICIANDO SEMBRADO NOCTURNO DE BANCO IA")
    print("=======================================")
    
    ChromaService.initialize()
    
    competencias_estrategicas = [
        "Razonamiento Cuantitativo",
    ]
    
    for ciclo in range(1, num_ciclos + 1):
        print(f"\n--- CICLO {ciclo} DE {num_ciclos} ---")
        for comp in competencias_estrategicas:
            modulo = get_modulo(programa, comp)
            is_english = "ingl" in comp.lower()
            
            print(f"> Extrayendo lote de {comp}...")
            
            try:
                # Disparamos el minero directamente (cantidad=30 pide oversmaple de +45)
                await _background_question_miner(
                    programa=programa,
                    competencia=comp,
                    nivel_objetivo="A2" if is_english else None,
                    dificultad_objetivo="intermedio" if not is_english else None,
                    cantidad=30,
                    entrenamiento_general=False,
                    modulo=modulo,
                    is_english=is_english,
                    comp_meta=comp,
                    cache_key=f"pregen_{ciclo}_{comp}"
                )
                
                print(f"[OK] Minería de '{comp}' finalizada para el ciclo {ciclo}.")
            except Exception as e:
                print(f"[ERROR] Falló la minería de '{comp}': {e}")
            
            # Pausa de API limits
            print("Pausa antispam de 15 segundos...")
            await asyncio.sleep(15)
            
    print("\n=======================================")
    print("SEMBRADO NOCTURNO COMPLETADO.")
    print("Revisa ChromaDB para ver el tamaño del banco.")
    print("=======================================")

if __name__ == "__main__":
    programa_objetivo = sys.argv[1] if len(sys.argv) > 1 else "Ingeniería de Sistemas"
    ciclos = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    asyncio.run(sembrar_banco(programa_objetivo, ciclos))
