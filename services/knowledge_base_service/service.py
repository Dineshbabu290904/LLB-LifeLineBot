"""Knowledge Base Service - CRUD for medical knowledge entries."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self):
        self._entries: Dict[str, dict] = {}

    async def startup(self):
        logger.info("Knowledge Base Service ready.")

    async def shutdown(self):
        pass

    async def add(self, title: str, content: str, category: str, source: Optional[str] = None) -> dict:
        entry_id = str(uuid.uuid4())
        entry = {
            "entry_id": entry_id, "title": title, "content": content,
            "category": category, "source": source,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._entries[entry_id] = entry
        return entry

    async def search(self, query: str, category: Optional[str] = None, limit: int = 10) -> dict:
        query_lower = query.lower()
        results = []
        for entry in self._entries.values():
            if category and entry["category"] != category:
                continue
            if query_lower in entry["title"].lower() or query_lower in entry["content"].lower():
                results.append(entry)
        return {"results": results[:limit], "total": len(results)}

    async def delete(self, entry_id: str) -> dict:
        if entry_id not in self._entries:
            return {"error": f"Entry {entry_id} not found"}
        del self._entries[entry_id]
        return {"deleted": True, "entry_id": entry_id}
