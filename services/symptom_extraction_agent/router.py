"""Symptom Extraction Router."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/symptom-extraction", tags=["symptom-extraction"])

def _svc(request: Request):
    return request.app.state.service

class ExtractRequest(BaseModel):
    text: str

class StructureRequest(BaseModel):
    symptoms: List[str]
    patient_id: Optional[str] = None

@router.post("/extract")
async def extract(req: ExtractRequest, request: Request):
    return await _svc(request).extract(req.text)

@router.post("/structure")
async def structure(req: StructureRequest, request: Request):
    return await _svc(request).structure(req.symptoms, req.patient_id)
