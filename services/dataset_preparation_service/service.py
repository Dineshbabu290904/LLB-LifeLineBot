"""Dataset Preparation Service - prepares and formats datasets for training."""
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    class Config:
        env_prefix = "DATASET_PREP_"

settings = Settings()


class DatasetPreparationService:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    async def startup(self):
        logger.info("DatasetPreparationService started")

    async def shutdown(self):
        pass

    def _format_entry(self, entry: Dict[str, Any], fmt: str) -> Dict[str, Any]:
        q = entry.get("question", "")
        a = entry.get("answer", "")
        if fmt == "chat":
            return {"messages": [{"role": "user", "content": q}, {"role": "assistant", "content": a}]}
        elif fmt == "completion":
            return {"prompt": f"Q: {q}\nA:", "completion": f" {a}"}
        else:
            return {"input": q, "output": a, "metadata": {k: v for k, v in entry.items() if k not in ("question", "answer")}}

    async def prepare_dataset(
        self,
        examples: List[Dict[str, Any]],
        output_format: str = "chat",
        shuffle: bool = True,
        seed: int = 42,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {"status": "running", "created_at": datetime.now(timezone.utc).isoformat()}

        if shuffle:
            random.seed(seed)
            examples = examples.copy()
            random.shuffle(examples)

        n = len(examples)
        train_end = int(n * settings.train_ratio)
        val_end = train_end + int(n * settings.val_ratio)

        train = [self._format_entry(e, output_format) for e in examples[:train_end]]
        val = [self._format_entry(e, output_format) for e in examples[train_end:val_end]]
        test = [self._format_entry(e, output_format) for e in examples[val_end:]]

        self._jobs[job_id] = {
            "status": "completed",
            "total": n,
            "train_count": len(train),
            "val_count": len(val),
            "test_count": len(test),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "job_id": job_id,
            "format": output_format,
            "splits": {"train": train, "validation": val, "test": test},
            "counts": {"total": n, "train": len(train), "validation": len(val), "test": len(test)},
        }

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        return {"job_id": job_id, **job}
