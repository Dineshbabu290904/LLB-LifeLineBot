"""Metadata Storage Service - stores metadata for documents, embeddings, datasets."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class MetadataStorageService:
    def __init__(self):
        self._store: Dict[str, Dict[str, dict]] = {}  # entity_type -> {entity_id -> metadata}

    async def startup(self):
        logger.info("Metadata Storage Service ready.")

    async def shutdown(self):
        pass

    async def store(self, entity_type: str, entity_id: str, metadata: Dict[str, Any]) -> dict:
        if entity_type not in self._store:
            self._store[entity_type] = {}
        record = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store[entity_type][entity_id] = record
        return record

    async def get(self, entity_type: str, entity_id: str) -> Optional[dict]:
        return self._store.get(entity_type, {}).get(entity_id)

    async def delete(self, entity_type: str, entity_id: str) -> dict:
        if entity_type in self._store and entity_id in self._store[entity_type]:
            del self._store[entity_type][entity_id]
            return {"deleted": True, "entity_type": entity_type, "entity_id": entity_id}
        return {"deleted": False, "error": "Not found"}
