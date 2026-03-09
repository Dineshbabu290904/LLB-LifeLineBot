"""Knowledge Base Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge-base", tags=["knowledge-base"])

def _svc(request: Request):
    return request.app.state.service

class AddRequest(BaseModel):
    title: str
    content: str
    category: str
    source: Optional[str] = None

@router.post("/add")
async def add(req: AddRequest, request: Request):
    return await _svc(request).add(req.title, req.content, req.category, req.source)

@router.get("/search")
async def search(query: str, category: Optional[str] = None, limit: int = 10, request: Request = None):
    return await _svc(request).search(query, category, limit)

@router.delete("/{entry_id}")
async def delete(entry_id: str, request: Request):
    return await _svc(request).delete(entry_id)
