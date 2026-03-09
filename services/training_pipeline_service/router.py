"""Training Pipeline Router."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/training-pipeline", tags=["training-pipeline"])

def _svc(request: Request):
    return request.app.state.service

class StartPipelineRequest(BaseModel):
    base_model: str
    dataset_id: str
    config: Dict[str, Any] = {}

@router.post("/start")
async def start(req: StartPipelineRequest, request: Request):
    return await _svc(request).start(req.base_model, req.dataset_id, req.config)

@router.get("/status/{pipeline_id}")
async def get_status(pipeline_id: str, request: Request):
    return await _svc(request).get_status(pipeline_id)

@router.post("/cancel/{pipeline_id}")
async def cancel(pipeline_id: str, request: Request):
    return await _svc(request).cancel(pipeline_id)
