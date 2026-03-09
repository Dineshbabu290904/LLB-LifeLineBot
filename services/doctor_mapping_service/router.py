"""Doctor Mapping Router."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/doctor-mapping", tags=["doctor-mapping"])

def _svc(request: Request):
    return request.app.state.service

class MappingRequest(BaseModel):
    symptoms: List[str]
    additional_context: Optional[str] = ""

@router.post("/map")
async def map_symptoms(req: MappingRequest, request: Request):
    svc = _svc(request)
    return svc.map_to_specialty(req.symptoms, req.additional_context or "")

@router.get("/specialties")
async def list_specialties(request: Request):
    svc = _svc(request)
    return {"specialties": svc.list_specialties()}
