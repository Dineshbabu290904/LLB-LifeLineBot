"""Vector Search Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/vector-search", tags=["vector-search"])

def _svc(request: Request):
    return request.app.state.service

class SearchRequest(BaseModel):
    query: str
    query_vector: Optional[List[float]] = None
    top_k: int = 10
    filters: Dict[str, Any] = {}

class BatchSearchRequest(BaseModel):
    queries: List[str]
    top_k: int = 10

class UpsertRequest(BaseModel):
    vectors: List[Dict[str, Any]]

@router.post("/search")
async def search(req: SearchRequest, request: Request):
    return await _svc(request).search(req.query, req.query_vector, req.top_k, req.filters)

@router.post("/batch")
async def batch_search(req: BatchSearchRequest, request: Request):
    return await _svc(request).batch_search(req.queries, req.top_k)

@router.post("/upsert")
async def upsert(req: UpsertRequest, request: Request):
    return await _svc(request).upsert(req.vectors)
