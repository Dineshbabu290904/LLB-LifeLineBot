"""PubMed Search Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pubmed-search", tags=["pubmed-search"])

def _svc(request: Request):
    return request.app.state.service

class SearchRequest(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)
    date_range: Optional[str] = None

@router.post("/search")
async def search_pubmed(req: SearchRequest, request: Request):
    svc = _svc(request)
    return await svc.search(req.query, req.max_results, req.date_range)

@router.get("/article/{pmid}")
async def get_article(pmid: str, request: Request):
    svc = _svc(request)
    return await svc.get_article(pmid)
