import sys
import asyncio
from app.routes.sugerencias import _background_question_miner, _get_docs_for_modulo
from app.services.chroma_client import ChromaService

async def test():
    ChromaService.initialize()
    collection = ChromaService.get_collection()
    
    # Vamos a forzar el log de preguntas
    # Hacemos un monkey patch a _almacenar_preguntas_db para ver que se guardaría
    import app.routes.sugerencias as sug
    original_almacenar = sug._almacenar_preguntas_db
    def print_almacenar(coll, pregs, mod):
        print(f"!!! INTENTO DE ALMACENAR: {len(pregs)} preguntas !!!")
        if pregs:
            print("EJEMPLO:", pregs[0])
        original_almacenar(coll, pregs, mod)
    sug._almacenar_preguntas_db = print_almacenar
    
    print("Iniciando prueba Escrita...")
    await _background_question_miner(
        programa="Ingeniería de Sistemas",
        competencia="Comunicación Escrita",
        nivel_objetivo=None,
        dificultad_objetivo="intermedio",
        cantidad=1,
        entrenamiento_general=False,
        modulo="general",
        is_english=False,
        comp_meta="Comunicación Escrita",
        cache_key="test_escr"
    )
    print("Iniciando prueba Ingles...")
    await _background_question_miner(
        programa="Ingeniería de Sistemas",
        competencia="Inglés",
        nivel_objetivo="A2",
        dificultad_objetivo=None,
        cantidad=5,
        entrenamiento_general=False,
        modulo="general",
        is_english=True,
        comp_meta="Inglés",
        cache_key="test_ingl"
    )

if __name__ == '__main__':
    asyncio.run(test())
