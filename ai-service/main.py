"""
Microservicio IA – Asistente Virtual Saber Pro
FastAPI + ChromaDB + Gemini Flash + sentence-transformers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.routes import consultar, sugerencias, reportes
from app.services.chroma_client import ChromaService

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa ChromaDB al arrancar. Si falla, lo reintenta en el primer request."""
    try:
        ChromaService.initialize()
        logger.info("[AI Service] ChromaDB conectado exitosamente.")
    except Exception as e:
        logger.warning(f"[AI Service] ChromaDB no disponible al arrancar: {e}. Se reintentará en el primer request.")
    yield


app = FastAPI(
    title="Asistente Saber Pro – IA Service",
    description="Microservicio de IA con pipeline RAG para preparación de pruebas Saber Pro",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consultar.router, prefix="/consultar", tags=["RAG"])
app.include_router(sugerencias.router, prefix="/sugerencias", tags=["Práctica"])
app.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])


@app.get("/health")
async def health():
    try:
        col = ChromaService.get_collection()
        chroma_status = f"ok ({col.count()} docs)"
    except Exception as e:
        chroma_status = f"error: {e}"
    return {
        "status": "ok",
        "service": "ai-service",
        "chroma": chroma_status,
    }
