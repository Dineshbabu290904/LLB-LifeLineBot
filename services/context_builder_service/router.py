"""Context Builder Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/context-builder", tags=["context-builder"])

def _svc(request: Request):
    return request.app.state.service

class BuildRequest(BaseModel):
    conversation_history: List[Dict[str, Any]] = []
    retrieved_knowledge: List[str] = []
    system_prompt: Optional[str] = None
    max_tokens: int = 4000

class TruncateRequest(BaseModel):
    context: List[Dict[str, Any]]
    max_tokens: int = 4000

@router.post("/build")
async def build_context(req: BuildRequest, request: Request):
    svc = _svc(request)
    return svc.build_context(req.conversation_history, req.retrieved_knowledge, req.system_prompt, req.max_tokens)

@router.post("/truncate")
async def truncate_context(req: TruncateRequest, request: Request):
    svc = _svc(request)
    return svc.truncate_context(req.context, req.max_tokens)
