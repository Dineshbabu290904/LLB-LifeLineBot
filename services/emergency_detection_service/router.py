"""Emergency Detection Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/emergency-detection", tags=["emergency-detection"])

def _svc(request: Request):
    return request.app.state.service

class DetectRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class AlertRequest(BaseModel):
    query: str
    user_id: str
    contact: Optional[str] = None

@router.post("/detect")
async def detect(req: DetectRequest, request: Request):
    return await _svc(request).detect(req.query, req.user_id)

@router.post("/alert")
async def alert(req: AlertRequest, request: Request):
    return await _svc(request).alert(req.query, req.user_id, req.contact)
