"""Medical Source Validation Router."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/medical-source-validation", tags=["medical-source-validation"])

def _svc(request: Request):
    return request.app.state.service

class ValidateRequest(BaseModel):
    source: str
    claim: Optional[str] = None

class BatchValidateRequest(BaseModel):
    sources: List[str]

@router.post("/validate")
async def validate(req: ValidateRequest, request: Request):
    return await _svc(request).validate(req.source, req.claim)

@router.post("/batch")
async def batch_validate(req: BatchValidateRequest, request: Request):
    return await _svc(request).batch_validate(req.sources)
