"""RAG Agent Service - full Retrieve-Augment-Generate pipeline."""
import logging
import httpx
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

VECTOR_SEARCH_URL = os.getenv("VECTOR_SEARCH_URL", "http://vector_search_service:8056")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://embedding_generation_service:8054")

class RAGAgentService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("RAG Agent Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def retrieve(self, query: str, top_k: int = 5) -> List[dict]:
        try:
            resp = await self._client.post(
                f"{VECTOR_SEARCH_URL}/api/v1/vector-search/search",
                json={"query": query, "top_k": top_k}
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

    async def generate(self, query: str, context_docs: List[dict]) -> str:
        context = "\n\n".join(doc.get("content", doc.get("text", "")) for doc in context_docs)
        prompt = f"""You are MEDBOT, a medical AI assistant. Use the following context to answer the question accurately and safely.

Context:
{context}

Question: {query}

Answer:"""
        try:
            resp = await self._client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False}
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"Generation failed: {e}"

    async def query(self, query: str, top_k: int = 5) -> dict:
        docs = await self.retrieve(query, top_k)
        answer = await self.generate(query, docs)
        return {
            "query": query,
            "answer": answer,
            "retrieved_docs": docs,
            "num_docs_used": len(docs),
        }

    async def retrieve_only(self, query: str, top_k: int = 5) -> dict:
        docs = await self.retrieve(query, top_k)
        return {"query": query, "results": docs, "total": len(docs)}
