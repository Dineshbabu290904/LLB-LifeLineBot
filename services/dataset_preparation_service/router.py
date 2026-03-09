"""Dataset Preparation Router."""
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dataset-preparation", tags=["dataset-preparation"])

def _svc(request: Request):
    return request.app.state.service

class PrepareRequest(BaseModel):
    examples: List[Dict[str, Any]]
    output_format: str = "chat"
    shuffle: bool = True
    seed: int = 42

@router.post("/prepare")
async def prepare_dataset(req: PrepareRequest, request: Request):
    svc = _svc(request)
    return await svc.prepare_dataset(req.examples, req.output_format, req.shuffle, req.seed)

@router.get("/status/{job_id}")
async def get_status(job_id: str, request: Request):
    svc = _svc(request)
    result = svc.get_status(job_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
