"""Vector Index Service - manages vector indices."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class VectorIndexService:
    def __init__(self):
        self._indices: Dict[str, dict] = {}
        self._vectors: Dict[str, List[dict]] = {}

    async def startup(self):
        logger.info("Vector Index Service ready.")

    async def shutdown(self):
        pass

    async def create_index(self, name: str, dimension: int, metric: str = "cosine") -> dict:
        index_id = str(uuid.uuid4())
        index = {
            "index_id": index_id, "name": name, "dimension": dimension,
            "metric": metric, "vector_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._indices[index_id] = index
        self._vectors[index_id] = []
        return index

    async def delete_index(self, index_id: str) -> dict:
        if index_id not in self._indices:
            return {"error": f"Index {index_id} not found"}
        del self._indices[index_id]
        del self._vectors[index_id]
        return {"deleted": True, "index_id": index_id}

    async def add_vectors(self, index_id: str, vectors: List[Dict[str, Any]]) -> dict:
        if index_id not in self._indices:
            return {"error": f"Index {index_id} not found"}
        for vec in vectors:
            vec_id = vec.get("id", str(uuid.uuid4()))
            self._vectors[index_id].append({
                "id": vec_id,
                "vector": vec.get("vector", []),
                "metadata": vec.get("metadata", {}),
                "added_at": datetime.now(timezone.utc).isoformat()
            })
        self._indices[index_id]["vector_count"] = len(self._vectors[index_id])
        return {"index_id": index_id, "added": len(vectors), "total": len(self._vectors[index_id])}

    async def list_indices(self) -> dict:
        return {"indices": list(self._indices.values()), "total": len(self._indices)}
