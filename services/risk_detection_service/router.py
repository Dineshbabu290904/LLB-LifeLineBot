"""Risk Detection Router."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/risk-detection", tags=["risk-detection"])

def _svc(request: Request):
    return request.app.state.service

class DetectRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

class AssessRequest(BaseModel):
    text: str
    age: Optional[int] = None
    medical_history: Optional[List[str]] = None

@router.post("/detect")
async def detect(req: DetectRequest, request: Request):
    return await _svc(request).detect(req.text, req.user_id)

@router.post("/assess")
async def assess(req: AssessRequest, request: Request):
    return await _svc(request).assess(req.text, req.age, req.medical_history)
