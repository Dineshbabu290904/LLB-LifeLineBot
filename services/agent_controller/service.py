"""Agent Controller Service - orchestrates and routes requests to agents."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    request_timeout: int = 30
    triage_agent_url: str = "http://triage_agent:8015"
    rag_agent_url: str = "http://rag_agent_service:8025"
    reasoning_agent_url: str = "http://reasoning_agent_service:8026"
    safety_guardrail_url: str = "http://safety_guardrail_agent:8027"
    search_agent_url: str = "http://search_agent_service:8028"
    vision_agent_url: str = "http://vision_agent_service:8023"
    knowledge_agent_url: str = "http://knowledge_agent_service:8021"

    class Config:
        env_prefix = "AGENT_CONTROLLER_"


settings = Settings()

AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "triage_agent": {"url": settings.triage_agent_url, "port": 8015, "capabilities": ["triage", "routing"]},
    "rag_agent": {"url": settings.rag_agent_url, "port": 8025, "capabilities": ["rag", "retrieval", "generation"]},
    "reasoning_agent": {"url": settings.reasoning_agent_url, "port": 8026, "capabilities": ["reasoning", "clinical"]},
    "safety_guardrail": {"url": settings.safety_guardrail_url, "port": 8027, "capabilities": ["safety", "filtering"]},
    "search_agent": {"url": settings.search_agent_url, "port": 8028, "capabilities": ["search", "semantic"]},
    "vision_agent": {"url": settings.vision_agent_url, "port": 8023, "capabilities": ["vision", "image"]},
    "knowledge_agent": {"url": settings.knowledge_agent_url, "port": 8021, "capabilities": ["knowledge", "retrieval"]},
}


class AgentControllerService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        logger.info("AgentControllerService started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Service not started")
        return self._client

    def _select_agent(self, task_type: str) -> str:
        task_lower = task_type.lower()
        if any(k in task_lower for k in ["triage", "assess", "urgency"]):
            return "triage_agent"
        if any(k in task_lower for k in ["image", "vision", "xray", "scan"]):
            return "vision_agent"
        if any(k in task_lower for k in ["reason", "clinical", "differential"]):
            return "reasoning_agent"
        if any(k in task_lower for k in ["search", "find"]):
            return "search_agent"
        if any(k in task_lower for k in ["knowledge", "retrieve"]):
            return "knowledge_agent"
        return "rag_agent"

    async def dispatch(self, task_type: str, payload: Dict[str, Any], agent_id: Optional[str] = None) -> Dict[str, Any]:
        agent_name = agent_id or self._select_agent(task_type)
        agent = AGENT_REGISTRY.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}", "task_id": str(uuid.uuid4())}

        task_id = str(uuid.uuid4())
        logger.info("Dispatching task %s to %s", task_id, agent_name)
        try:
            resp = await self.client.post(
                f"{agent['url']}/api/v1/{agent_name.replace('_', '-')}/dispatch",
                json={"task_id": task_id, "task_type": task_type, **payload},
            )
            resp.raise_for_status()
            return {"task_id": task_id, "agent": agent_name, "result": resp.json()}
        except Exception as exc:
            logger.warning("Dispatch to %s failed: %s", agent_name, exc)
            return {"task_id": task_id, "agent": agent_name, "error": str(exc)}

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {"agent_id": name, "port": info["port"], "capabilities": info["capabilities"]}
            for name, info in AGENT_REGISTRY.items()
        ]

    async def health_check_all(self) -> Dict[str, Any]:
        results = {}
        for name, info in AGENT_REGISTRY.items():
            try:
                resp = await self.client.get(f"{info['url']}/health", timeout=5.0)
                results[name] = {"status": "healthy" if resp.status_code == 200 else "unhealthy", "port": info["port"]}
            except Exception as exc:
                results[name] = {"status": "unreachable", "error": str(exc), "port": info["port"]}
        return {"checked_at": datetime.now(timezone.utc).isoformat(), "agents": results}
