"""Embedding Generation Service - generates vector embeddings via embedding model."""
import logging
import httpx
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_URL = os.getenv("EMBEDDING_MODEL_URL", "http://embedding_model_service:8052")

class EmbeddingGenerationService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info("Embedding Generation Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def embed(self, text: str, model: str = "nomic-embed-text") -> dict:
        try:
            resp = await self._client.post(f"{EMBEDDING_MODEL_URL}/api/v1/embed", json={"text": text, "model": model})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Embedding error: %s", e)
            return {"text": text, "embedding": [], "error": str(e)}

    async def embed_batch(self, texts: List[str], model: str = "nomic-embed-text") -> dict:
        results = []
        for text in texts:
            result = await self.embed(text, model)
            results.append(result)
        return {"embeddings": results, "total": len(results)}
