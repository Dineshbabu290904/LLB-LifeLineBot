"""Dataset Generation Agent - generates synthetic medical Q&A datasets."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8050"
    request_timeout: int = 120
    class Config:
        env_prefix = "DATASET_GEN_"

settings = Settings()

MEDICAL_TOPICS = [
    "cardiovascular diseases", "respiratory conditions", "diabetes management",
    "infectious diseases", "mental health", "pediatric care", "geriatric care",
    "emergency medicine", "oncology", "neurology", "orthopedics", "gastroenterology",
]

class DatasetGenerationAgent:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        logger.info("DatasetGenerationAgent started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Not started")
        return self._client

    async def generate_dataset(self, topic: str, num_entries: int = 10, difficulty: str = "medium") -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {"status": "running", "created_at": datetime.now(timezone.utc).isoformat()}

        prompt = f"""Generate {num_entries} medical Q&A pairs about {topic} at {difficulty} difficulty level.
Format each entry as:
Q: [clinical question]
A: [detailed medical answer]
CATEGORY: [medical category]
DIFFICULTY: {difficulty}

Generate realistic, educational medical content."""

        try:
            resp = await self.client.post(
                f"{settings.ollama_router_url}/api/v1/model/generate",
                json={"prompt": prompt, "task_type": "generation", "temperature": 0.7, "max_tokens": 2000},
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            entries = self._parse_qa_pairs(raw, topic, difficulty)
            self._jobs[job_id] = {
                "status": "completed",
                "entries_generated": len(entries),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            return {"job_id": job_id, "entries": entries, "count": len(entries), "topic": topic}
        except Exception as exc:
            logger.warning("Generation failed: %s", exc)
            entries = self._synthetic_entries(topic, num_entries, difficulty)
            self._jobs[job_id] = {"status": "completed_fallback", "entries_generated": len(entries)}
            return {"job_id": job_id, "entries": entries, "count": len(entries), "topic": topic}

    def _parse_qa_pairs(self, text: str, topic: str, difficulty: str) -> List[Dict[str, Any]]:
        entries = []
        blocks = text.split("\nQ:")
        for block in blocks:
            if "A:" in block:
                lines = block.strip().split("\n")
                q = lines[0].replace("Q:", "").strip() if lines else ""
                a_lines = []
                for line in lines[1:]:
                    if line.startswith("A:"):
                        a_lines.append(line.replace("A:", "").strip())
                    elif line.startswith("CATEGORY:") or line.startswith("DIFFICULTY:"):
                        break
                    else:
                        a_lines.append(line)
                if q and a_lines:
                    entries.append({
                        "id": str(uuid.uuid4()),
                        "question": q,
                        "answer": " ".join(a_lines).strip(),
                        "topic": topic,
                        "difficulty": difficulty,
                    })
        return entries or self._synthetic_entries(topic, 3, difficulty)

    def _synthetic_entries(self, topic: str, num: int, difficulty: str) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(uuid.uuid4()),
                "question": f"What are the key considerations in managing {topic}? (entry {i+1})",
                "answer": f"Management of {topic} requires careful assessment, evidence-based protocols, and individualized care planning.",
                "topic": topic,
                "difficulty": difficulty,
            }
            for i in range(min(num, 5))
        ]

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        return {"job_id": job_id, **job}
