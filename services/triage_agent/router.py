"""Triage Agent Router."""
import logging
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/triage", tags=["triage"])

def _svc(request: Request):
    return request.app.state.service

class TriageRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

@router.post("/assess")
async def assess(req: TriageRequest, request: Request):
    return await _svc(request).assess(req.query, req.user_id)

@router.post("/route")
async def route(req: TriageRequest, request: Request):
    return await _svc(request).route(req.query, req.user_id)
