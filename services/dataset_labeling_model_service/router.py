"""Dataset Labeling Router."""
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dataset-labeling", tags=["dataset-labeling"])

def _svc(request: Request):
    return request.app.state.service

class LabelRequest(BaseModel):
    examples: List[Dict[str, Any]]

class ValidateRequest(BaseModel):
    examples: List[Dict[str, Any]]

@router.post("/label")
async def label_batch(req: LabelRequest, request: Request):
    svc = _svc(request)
    return await svc.label_batch(req.examples)

@router.post("/validate")
async def validate_labeled(req: ValidateRequest, request: Request):
    svc = _svc(request)
    return svc.validate_labeled(req.examples)
