"""Knowledge Agent Router."""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge-agent", tags=["knowledge-agent"])

def _svc(request: Request):
    return request.app.state.service

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5

class ReasonRequest(BaseModel):
    query: str
    context: str

@router.post("/retrieve")
async def retrieve(req: RetrieveRequest, request: Request):
    return await _svc(request).retrieve(req.query, req.top_k)

@router.post("/reason")
async def reason(req: ReasonRequest, request: Request):
    return await _svc(request).reason(req.query, req.context)
