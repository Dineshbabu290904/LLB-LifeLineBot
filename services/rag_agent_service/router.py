"""RAG Agent Router."""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/rag-agent", tags=["rag-agent"])

def _svc(request: Request):
    return request.app.state.service

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/query")
async def query(req: QueryRequest, request: Request):
    return await _svc(request).query(req.query, req.top_k)

@router.post("/retrieve-only")
async def retrieve_only(req: QueryRequest, request: Request):
    return await _svc(request).retrieve_only(req.query, req.top_k)
