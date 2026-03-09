"""Agent Controller Router."""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent-controller", tags=["agent-controller"])


def _svc(request: Request):
    return request.app.state.service


class DispatchRequest(BaseModel):
    task_type: str
    agent_id: Optional[str] = None
    payload: Dict[str, Any] = {}


@router.post("/dispatch")
async def dispatch_task(req: DispatchRequest, request: Request):
    svc = _svc(request)
    result = await svc.dispatch(req.task_type, req.payload, req.agent_id)
    if "error" in result and "result" not in result:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result["error"])
    return result


@router.get("/agents")
async def list_agents(request: Request):
    svc = _svc(request)
    return {"agents": svc.list_agents()}


@router.post("/health-check")
async def health_check_all(request: Request):
    svc = _svc(request)
    return await svc.health_check_all()
