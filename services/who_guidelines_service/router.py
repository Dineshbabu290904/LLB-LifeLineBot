"""WHO Guidelines Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/who-guidelines", tags=["who-guidelines"])

def _svc(request: Request):
    return request.app.state.service

class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

@router.post("/search")
async def search(req: SearchRequest, request: Request):
    return await _svc(request).search(req.query, req.category)

@router.get("/guideline/{guideline_id}")
async def get_guideline(guideline_id: str, request: Request):
    result = await _svc(request).get_guideline(guideline_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Guideline {guideline_id} not found")
    return result
