"""Search Agent Router."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/search-agent", tags=["search-agent"])

def _svc(request: Request):
    return request.app.state.service

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Dict[str, Any] = {}

@router.post("/search")
async def search(req: SearchRequest, request: Request):
    return await _svc(request).hybrid_search(req.query, req.top_k, req.filters)

@router.post("/semantic")
async def semantic(req: SearchRequest, request: Request):
    return await _svc(request).semantic_search(req.query, req.top_k)
