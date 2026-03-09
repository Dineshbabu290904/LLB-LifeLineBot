"""Web Search Service - searches the web for medical information."""
import logging
import httpx
import os
from typing import List, Optional

logger = logging.getLogger(__name__)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

class WebSearchService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info("Web Search Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def search(self, query: str, num_results: int = 5) -> dict:
        if SERPER_API_KEY:
            try:
                resp = await self._client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": query, "num": num_results}
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")} for r in data.get("organic", [])]
            except Exception as e:
                logger.warning("Serper API failed: %s", e)
                results = []
        else:
            # Fallback: simulate results for testing
            results = [{"title": f"Medical Information: {query}", "url": "https://www.who.int/", "snippet": f"WHO guidelines and information about {query}"}]
        return {"query": query, "results": results, "total": len(results), "source": "web_search"}

    async def medical_search(self, query: str, num_results: int = 5) -> dict:
        medical_query = f"{query} site:who.int OR site:cdc.gov OR site:nih.gov OR site:mayoclinic.org"
        result = await self.search(medical_query, num_results)
        result["search_type"] = "medical_filtered"
        return result
