"""Vector Search Service - vector similarity search."""
import logging
import math
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory vector store (in production, use Qdrant/Chroma/Weaviate)
_store: List[dict] = []

def _cosine_sim(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

class VectorSearchService:
    def __init__(self):
        self._vectors: List[dict] = []

    async def startup(self):
        logger.info("Vector Search Service ready.")

    async def shutdown(self):
        pass

    async def upsert(self, vectors: List[Dict[str, Any]]) -> dict:
        added = 0
        for vec in vectors:
            vec_id = vec.get("id", str(uuid.uuid4()))
            existing = next((v for v in self._vectors if v["id"] == vec_id), None)
            if existing:
                existing.update(vec)
            else:
                self._vectors.append({"id": vec_id, "vector": vec.get("vector", []), "content": vec.get("content", ""), "metadata": vec.get("metadata", {})})
                added += 1
        return {"upserted": added, "total": len(self._vectors)}

    async def search(self, query: str, query_vector: Optional[List[float]] = None, top_k: int = 10, filters: dict = {}) -> dict:
        if query_vector:
            scored = [(v, _cosine_sim(query_vector, v["vector"])) for v in self._vectors]
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [{"id": v["id"], "content": v["content"], "metadata": v["metadata"], "score": score} for v, score in scored[:top_k]]
        else:
            # Text-based fallback
            query_lower = query.lower()
            results = [{"id": v["id"], "content": v["content"], "metadata": v["metadata"], "score": 0.5} for v in self._vectors if query_lower in v.get("content", "").lower()][:top_k]
        return {"query": query, "results": results, "total": len(results)}

    async def batch_search(self, queries: List[str], top_k: int = 10) -> dict:
        results = []
        for q in queries:
            r = await self.search(q, top_k=top_k)
            results.append(r)
        return {"batch_results": results, "total_queries": len(queries)}
