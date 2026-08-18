"""
Cliente ChromaDB persistente — compatible con ChromaDB v0.5+ (API v2).
Gestiona la colección de embeddings del asistente Saber Pro.
"""

import os

import chromadb
import httpx
from chromadb.config import Settings


class ChromaService:
    _client: chromadb.ClientAPI | None = None
    _collection = None

    COLLECTION_NAME = "saberpro_docs"

    @classmethod
    def initialize(cls):
        host = os.getenv("CHROMA_HOST", "chromadb")
        port = int(os.getenv("CHROMA_PORT", "8000"))

        # ChromaDB v0.5+ usa HttpClient sin tenant ni database por defecto.
        # Se conecta al host directamente y crea/obtiene la colección.
        cls._client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(anonymized_telemetry=False),
        )

        # Verificar conectividad antes de continuar
        try:
            cls._client.heartbeat()
        except Exception as e:
            raise RuntimeError(f"No se pudo conectar a ChromaDB en {host}:{port} — {e}")

        # Obtiene o crea la colección — RNF-12
        cls._collection = cls._client.get_or_create_collection(
            name=cls.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        count = cls._collection.count()
        print(f"[ChromaDB] Conectado. Colección '{cls.COLLECTION_NAME}': {count} documentos.")

    @classmethod
    def get_collection(cls):
        if cls._collection is None:
            cls.initialize()
        # Verificar que la colección sigue existiendo (puede haberse borrado y recreado)
        try:
            cls._collection.count()
        except Exception:
            # La referencia es stale; re-inicializar
            cls._collection = None
            cls._client = None
            cls.initialize()
        return cls._collection

    @classmethod
    def _raw_query(cls, embedding: list[float], n_results: int, where: dict | None) -> dict:
        """
        Workaround HTTP directo para el bug de collection.query() en ChromaDB
        v0.5.x: el cliente envía `where: {}` y el servidor lo rechaza con
        "Expected where to have exactly one operator, got {}".
        """
        host = os.getenv("CHROMA_HOST", "chromadb")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        collection_id = cls.get_collection().id

        payload = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            payload["where"] = where

        resp = httpx.post(
            f"http://{host}:{port}/api/v1/collections/{collection_id}/query",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def query(cls, embedding: list[float], programa: str, n_results: int = 5,
              where_extra: dict = None, modulo: str = None) -> dict:
        """
        RF-06: Búsqueda semántica filtrada por módulo y opcionalmente por tipo.
        modulo:     'general' (módulos comunes) o slug del programa (módulo específico).
        where_extra: filtros adicionales, ej: {"tipo": "ejemplo"}
        Cascada de fallbacks si no hay resultados con los filtros dados.
        """
        collection = cls.get_collection()

        if collection.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        n = min(n_results, collection.count())

        def build_where(include_modulo=True):
            conditions = []
            if include_modulo and modulo:
                conditions.append({"modulo": modulo})
            if where_extra:
                for k, v in where_extra.items():
                    conditions.append({k: v})
            if len(conditions) == 1:
                return conditions[0]
            if len(conditions) > 1:
                return {"$and": conditions}
            return None

        # Nivel 1: modulo + tipo
        try:
            return cls._raw_query(embedding, n, build_where(include_modulo=True))
        except Exception:
            pass

        # Nivel 2: solo tipo (sin filtro de módulo)
        try:
            return cls._raw_query(embedding, n, build_where(include_modulo=False))
        except Exception:
            pass

        # Nivel 3: sin ningún filtro
        return cls._raw_query(embedding, n, None)
