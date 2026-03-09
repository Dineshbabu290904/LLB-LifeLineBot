"""Web Search Router."""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/web-search", tags=["web-search"])

def _svc(request: Request):
    return request.app.state.service

class SearchRequest(BaseModel):
    query: str
    num_results: int = 5

@router.post("/search")
async def search(req: SearchRequest, request: Request):
    return await _svc(request).search(req.query, req.num_results)

@router.post("/medical")
async def medical_search(req: SearchRequest, request: Request):
    return await _svc(request).medical_search(req.query, req.num_results)
