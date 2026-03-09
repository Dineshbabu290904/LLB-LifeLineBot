"""Model Registry Service - registry for available LLM models."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ModelRegistryService:
    def __init__(self):
        self._models: Dict[str, dict] = {}
        # Pre-populate with known Ollama models
        for name, caps in [
            ("llama3.2:3b", ["text-generation", "medical-qa"]),
            ("llama3.2:1b", ["text-generation"]),
            ("nomic-embed-text", ["embedding"]),
            ("llava:7b", ["vision", "image-analysis"]),
        ]:
            mid = str(uuid.uuid4())
            self._models[mid] = {
                "model_id": mid, "name": name, "capabilities": caps,
                "status": "available", "provider": "ollama",
                "registered_at": datetime.now(timezone.utc).isoformat()
            }

    async def startup(self):
        logger.info("Model Registry Service ready with %d models.", len(self._models))

    async def shutdown(self):
        pass

    async def register(self, name: str, capabilities: List[str], provider: str = "ollama", metadata: dict = {}) -> dict:
        model_id = str(uuid.uuid4())
        model = {
            "model_id": model_id, "name": name, "capabilities": capabilities,
            "provider": provider, "metadata": metadata,
            "status": "available", "registered_at": datetime.now(timezone.utc).isoformat()
        }
        self._models[model_id] = model
        return model

    async def list_models(self, capability: Optional[str] = None) -> dict:
        models = list(self._models.values())
        if capability:
            models = [m for m in models if capability in m.get("capabilities", [])]
        return {"models": models, "total": len(models)}

    async def get_model(self, model_id: str) -> Optional[dict]:
        return self._models.get(model_id)
