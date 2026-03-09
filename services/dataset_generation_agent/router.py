"""Dataset Generation Agent Router."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dataset-generation", tags=["dataset-generation"])

def _svc(request: Request):
    return request.app.state.service

class GenerateRequest(BaseModel):
    topic: str
    num_entries: int = Field(default=10, ge=1, le=100)
    difficulty: str = "medium"

@router.post("/generate")
async def generate_dataset(req: GenerateRequest, request: Request):
    svc = _svc(request)
    return await svc.generate_dataset(req.topic, req.num_entries, req.difficulty)

@router.get("/status/{job_id}")
async def get_status(job_id: str, request: Request):
    svc = _svc(request)
    result = svc.get_status(job_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
