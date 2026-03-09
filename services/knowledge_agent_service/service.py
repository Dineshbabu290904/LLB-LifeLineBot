"""Knowledge Agent Service - retrieves and reasons over medical knowledge."""
import logging
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)

VECTOR_SEARCH_URL = os.getenv("VECTOR_SEARCH_URL", "http://vector_search_service:8056")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class KnowledgeAgentService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info("Knowledge Agent Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def retrieve(self, query: str, top_k: int = 5) -> dict:
        try:
            resp = await self._client.post(f"{VECTOR_SEARCH_URL}/api/v1/vector-search/search", json={"query": query, "top_k": top_k})
            resp.raise_for_status()
            results = resp.json()
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            results = {"results": [], "total": 0}
        return {"query": query, "retrieved_knowledge": results.get("results", []), "total": results.get("total", 0)}

    async def reason(self, query: str, context: str) -> dict:
        try:
            prompt = f"Using the following medical knowledge context:\n{context}\n\nAnswer the medical question: {query}"
            resp = await self._client.post(f"{OLLAMA_URL}/api/generate", json={"model": "llama3.2:3b", "prompt": prompt, "stream": False})
            resp.raise_for_status()
            answer = resp.json().get("response", "")
        except Exception as e:
            answer = f"Reasoning service unavailable: {e}"
        return {"query": query, "reasoning": answer, "sources_used": bool(context)}
