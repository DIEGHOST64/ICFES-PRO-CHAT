"""
RF-22: Endpoint POST /consultar — Pipeline RAG principal
Recibe pregunta + programa, consulta ChromaDB y responde con Gemini Flash.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.services.rag_service import rag_query

router = APIRouter()


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000,
                          description="Pregunta del estudiante en lenguaje natural")
    programa: str = Field(default="General", max_length=100,
                          description="Programa académico del estudiante")
    competencia: str | None = Field(default=None, max_length=100,
                                    description="Competencia activa (para routing de módulo)")

    @field_validator("programa", mode="before")
    @classmethod
    def normalizar_programa(cls, v):
        if not v or str(v).strip() == "":
            return "General"
        return str(v).strip()

    @field_validator("pregunta", mode="before")
    @classmethod
    def normalizar_pregunta(cls, v):
        if not v or str(v).strip() == "":
            raise ValueError("La pregunta no puede estar vacía.")
        return str(v).strip()


class ConsultaResponse(BaseModel):
    respuesta: str
    fuentes: list[str]
    tiempo_ms: int
    fragmentos_usados: int


@router.post("", response_model=ConsultaResponse)
async def consultar(body: ConsultaRequest):
    """
    Procesa una consulta estudiantil usando el pipeline RAG:
    1. Genera embedding de la pregunta
    2. Recupera fragmentos relevantes de ChromaDB (filtrado por programa)
    3. Envía contexto a Gemini Flash
    4. Retorna respuesta fundamentada con fuentes ICFES
    """
    try:
        result = await rag_query(
            pregunta=body.pregunta,
            programa=body.programa,
            competencia=body.competencia,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando la consulta: {str(e)}"
        )
