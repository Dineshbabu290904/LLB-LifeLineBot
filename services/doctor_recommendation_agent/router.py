"""Doctor Recommendation Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/doctor-recommendation", tags=["doctor-recommendation"])

def _svc(request: Request):
    return request.app.state.service

class RecommendRequest(BaseModel):
    symptoms: List[str]
    location: Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)

class RankRequest(BaseModel):
    doctors: List[Dict[str, Any]]
    criteria: Dict[str, Any] = {}

@router.post("/recommend")
async def recommend(req: RecommendRequest, request: Request):
    svc = _svc(request)
    return await svc.recommend(req.symptoms, req.location, req.max_results)

@router.post("/rank")
async def rank_doctors(req: RankRequest, request: Request):
    svc = _svc(request)
    return await svc.rank_doctors(req.doctors, req.criteria)
