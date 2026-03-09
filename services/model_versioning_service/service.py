"""Model Versioning Service - manages model versions."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ModelVersioningService:
    def __init__(self):
        self._versions: Dict[str, dict] = {}  # version_id -> version info
        self._model_versions: Dict[str, List[str]] = {}  # model_id -> [version_ids]

    async def startup(self):
        logger.info("Model Versioning Service ready.")

    async def shutdown(self):
        pass

    async def create_version(self, model_id: str, version_tag: str, config: dict, metrics: dict = {}) -> dict:
        version_id = str(uuid.uuid4())
        version = {
            "version_id": version_id, "model_id": model_id, "version_tag": version_tag,
            "config": config, "metrics": metrics, "status": "staging",
            "is_production": False, "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._versions[version_id] = version
        self._model_versions.setdefault(model_id, []).append(version_id)
        return version

    async def list_versions(self, model_id: str) -> dict:
        version_ids = self._model_versions.get(model_id, [])
        versions = [self._versions[vid] for vid in version_ids if vid in self._versions]
        return {"model_id": model_id, "versions": versions, "total": len(versions)}

    async def promote(self, version_id: str) -> dict:
        if version_id not in self._versions:
            return {"error": f"Version {version_id} not found"}
        version = self._versions[version_id]
        model_id = version["model_id"]
        # Demote current production
        for vid in self._model_versions.get(model_id, []):
            if vid in self._versions and self._versions[vid]["is_production"]:
                self._versions[vid]["is_production"] = False
                self._versions[vid]["status"] = "retired"
        version["is_production"] = True
        version["status"] = "production"
        version["promoted_at"] = datetime.now(timezone.utc).isoformat()
        return version
