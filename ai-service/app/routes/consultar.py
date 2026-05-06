"""
RF-22: Endpoint POST /consultar — Pipeline RAG principal
Recibe pregunta + programa, consulta ChromaDB y responde con Gemini Flash.
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.services.rag_service import rag_query, rag_query_stream
from app.services.gemini_client import generate_guide_image, generate_visual_aids

router = APIRouter()


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    programa: str = Field(default="General", max_length=100)
    competencia: str | None = Field(default=None, max_length=100)
    nombre_estudiante: str = Field(default="", max_length=150)
    historial: list[dict] = Field(default_factory=list)

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


class GuiaImagenRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    respuesta: str = Field(..., min_length=1, max_length=8000)
    programa: str = Field(default="General", max_length=100)


@router.post("", response_model=ConsultaResponse)
async def consultar(body: ConsultaRequest):
    try:
        result = await rag_query(
            pregunta=body.pregunta,
            programa=body.programa,
            nombre=body.nombre_estudiante,
            competencia=body.competencia,
            historial=body.historial,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando la consulta: {str(e)}")


@router.post("/stream")
async def consultar_stream(body: ConsultaRequest):
    """
    Versión SSE del pipeline RAG — los chunks de Gemini llegan en tiempo real.
    Formato: data: {"fuentes":[...]}  → data: {"chunk":"..."}  → data: [DONE]
    """
    async def event_generator():
        try:
            async for event in rag_query_stream(
                pregunta=body.pregunta,
                programa=body.programa,
                nombre=body.nombre_estudiante,
                competencia=body.competencia,
                historial=body.historial,
            ):
                if isinstance(event, dict):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'chunk': event}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/guia-imagen")
async def guia_imagen(body: GuiaImagenRequest):
    """Genera una imagen guía opcional basada en pregunta y respuesta del chat."""
    try:
        image_result = await generate_guide_image(
            pregunta=body.pregunta,
            respuesta=body.respuesta,
            programa=body.programa,
        )
        aids = await generate_visual_aids(
            pregunta=body.pregunta,
            respuesta=body.respuesta,
            programa=body.programa,
        )
        return {
            "image_data_url": image_result.get("image_data_url") if image_result else None,
            "caption": image_result.get("caption") if image_result else None,
            "image_model_used": image_result.get("model_used") if image_result else None,
            "image_error": image_result.get("error") if image_result else None,
            "latex_formula": aids.get("latex_formula", ""),
            "latex_explanation": aids.get("latex_explanation", ""),
            "guide_title": aids.get("guide_title", "Guia visual paso a paso"),
            "guide_steps": aids.get("guide_steps", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando guia visual: {str(e)}")


# ======================================================================
# Chat del Gestor de Conocimiento
# ======================================================================
class AdminChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=2000)
    dashboard_data: dict = Field(default_factory=dict)
    historial: list[dict] = Field(default_factory=list)

@router.post("/admin-chat")
async def admin_chat(payload: AdminChatRequest):
    """Chat IA con acceso a todos los datos del dashboard para el gestor."""
    try:
        from app.services.gemini_client import get_gemini_model
        model = get_gemini_model()
        data = payload.dashboard_data
        pregunta = payload.pregunta
        
        ctx = "=== DATOS DEL DASHBOARD ===\n\n"
        
        if data.get("metrics"):
            m = data["metrics"]
            ctx += f"Metricas: {m.get('total_consultas','?')} consultas totales, "
            ctx += f"{m.get('estudiantes_unicos','?')} estudiantes unicos, "
            ctx += f"{m.get('consultas_hoy','?')} consultas hoy, "
            ctx += f"{m.get('promedio_positivas','?')} positivas, "
            ctx += f"{m.get('total_estudiantes','?')} total estudiantes.\n"
        
        if data.get("by_program"):
            ctx += "\nTODOS LOS PROGRAMAS:\n"
            for p in data["by_program"]:
                ctx += f"  - {p.get('programa','?')}: {p.get('total',0)} consultas\n"

        if data.get("practice_competencies"):
            ctx += "\nTODAS LAS COMPETENCIAS:\n"
            for c in data["practice_competencies"]:
                ctx += f"  - {c.get('competencia','?')} ({c.get('programa','?')}): "
                ctx += f"{c.get('promedio_competencia',0)}% ({c.get('aciertos',0)}/{c.get('intentos',0)})\n"
        
        if data.get("difficulty_distribution"):
            ctx += "\nDistribucion por dificultad:\n"
            for d in data["difficulty_distribution"]:
                ctx += f"  - {d.get('competencia','?')} [{d.get('nivel_pregunta','?')}]: {d.get('total',0)}\n"
        
        if data.get("level_progression"):
            ctx += f"\nProgresion de nivel: {len(data['level_progression'])} registros.\n"
        
        hist = ""
        for msg in payload.historial[-6:]:
            role = "Gestor" if msg.get("role") == "user" else "IA"
            hist += f"{role}: {msg.get('content','')}\n"
        
        prompt = (
            "Eres un consultor academico con acceso total a los datos del dashboard Saber Pro. "
            "Responde de forma conversacional, directa y basada en DATOS REALES. "
            "Si preguntan por un estudiante o programa, busca en el contexto. "
            "Usa Markdown para estructurar respuestas largas. Max 300 palabras. "
            "Si no hay datos suficientes, dilo con honestidad.\n\n"
            f"{ctx[:8000]}\n\n"
            f"=== HISTORIAL ===\n{hist}\n\n"
            f"=== PREGUNTA ===\n{pregunta}\n"
        )
        
        resp = model.generate_content(prompt)
        return {"respuesta": (resp.text or "").strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en chat admin: {str(e)}")
