"""Safety Guardrail Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/safety-guardrail", tags=["safety-guardrail"])

def _svc(request: Request):
    return request.app.state.service

class InputCheckRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

class OutputCheckRequest(BaseModel):
    text: str

class FilterRequest(BaseModel):
    text: str
    add_disclaimer: bool = True

@router.post("/check-input")
async def check_input(req: InputCheckRequest, request: Request):
    return await _svc(request).check_input(req.text, req.user_id)

@router.post("/check-output")
async def check_output(req: OutputCheckRequest, request: Request):
    return await _svc(request).check_output(req.text)

@router.post("/filter")
async def filter_output(req: FilterRequest, request: Request):
    return await _svc(request).filter(req.text, req.add_disclaimer)
