"""Reasoning Agent Router."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reasoning-agent", tags=["reasoning-agent"])

def _svc(request: Request):
    return request.app.state.service

class ReasonRequest(BaseModel):
    question: str
    patient_context: Optional[str] = None

class DifferentialRequest(BaseModel):
    symptoms: List[str]
    patient_context: Optional[str] = None

@router.post("/reason")
async def reason(req: ReasonRequest, request: Request):
    return await _svc(request).reason(req.question, req.patient_context)

@router.post("/differential")
async def differential(req: DifferentialRequest, request: Request):
    return await _svc(request).differential(req.symptoms, req.patient_context)
