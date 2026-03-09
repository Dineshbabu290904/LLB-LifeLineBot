"""Training Pipeline Service - orchestrates the full model training pipeline."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PIPELINE_STAGES = ["data_preparation", "fine_tuning", "evaluation", "validation", "deployment"]

class TrainingPipelineService:
    def __init__(self):
        self._pipelines: Dict[str, dict] = {}

    async def startup(self):
        logger.info("Training Pipeline Service ready.")

    async def shutdown(self):
        pass

    async def start(self, base_model: str, dataset_id: str, config: dict) -> dict:
        pipeline_id = str(uuid.uuid4())
        pipeline = {
            "pipeline_id": pipeline_id,
            "base_model": base_model,
            "dataset_id": dataset_id,
            "config": config,
            "status": "running",
            "current_stage": "data_preparation",
            "stages": {s: "pending" for s in PIPELINE_STAGES},
            "progress_pct": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "output_model_id": None,
        }
        pipeline["stages"]["data_preparation"] = "running"
        self._pipelines[pipeline_id] = pipeline
        logger.info("Training pipeline %s started for model %s", pipeline_id, base_model)
        return pipeline

    async def get_status(self, pipeline_id: str) -> dict:
        if pipeline_id not in self._pipelines:
            return {"error": f"Pipeline {pipeline_id} not found"}
        return self._pipelines[pipeline_id]

    async def cancel(self, pipeline_id: str) -> dict:
        if pipeline_id not in self._pipelines:
            return {"error": f"Pipeline {pipeline_id} not found"}
        self._pipelines[pipeline_id]["status"] = "cancelled"
        self._pipelines[pipeline_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        return {"pipeline_id": pipeline_id, "status": "cancelled"}
