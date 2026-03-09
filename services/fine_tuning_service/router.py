"""Fine-tuning Router."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/fine-tuning", tags=["fine-tuning"])

def _svc(request: Request):
    return request.app.state.service

class StartJobRequest(BaseModel):
    base_model: str
    dataset_id: str
    config: Dict[str, Any] = {}

@router.post("/start")
async def start_job(req: StartJobRequest, request: Request):
    return await _svc(request).start_job(req.base_model, req.dataset_id, req.config)

@router.get("/status/{job_id}")
async def get_status(job_id: str, request: Request):
    return await _svc(request).get_status(job_id)

@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str, request: Request):
    return await _svc(request).cancel_job(job_id)
