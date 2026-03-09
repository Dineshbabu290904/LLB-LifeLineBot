"""Search Agent Service - hybrid vector + keyword search."""
import logging
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)
VECTOR_SEARCH_URL = os.getenv("VECTOR_SEARCH_URL", "http://vector_search_service:8056")

class SearchAgentService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info("Search Agent Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def hybrid_search(self, query: str, top_k: int = 10, filters: dict = {}) -> dict:
        try:
            resp = await self._client.post(
                f"{VECTOR_SEARCH_URL}/api/v1/vector-search/search",
                json={"query": query, "top_k": top_k, "filters": filters}
            )
            resp.raise_for_status()
            vector_results = resp.json().get("results", [])
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            vector_results = []
        return {
            "query": query,
            "results": vector_results,
            "total": len(vector_results),
            "search_type": "hybrid",
        }

    async def semantic_search(self, query: str, top_k: int = 10) -> dict:
        try:
            resp = await self._client.post(
                f"{VECTOR_SEARCH_URL}/api/v1/vector-search/search",
                json={"query": query, "top_k": top_k}
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            logger.warning("Semantic search failed: %s", e)
            results = []
        return {"query": query, "results": results, "total": len(results), "search_type": "semantic"}
