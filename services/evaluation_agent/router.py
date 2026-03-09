"""Evaluation Agent Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])

def _svc(request: Request):
    return request.app.state.service

class EvalRequest(BaseModel):
    query: str
    response: str
    ground_truth: Optional[str] = None

class BatchEvalRequest(BaseModel):
    items: List[Dict[str, Any]]

@router.post("/evaluate")
async def evaluate(req: EvalRequest, request: Request):
    return await _svc(request).evaluate(req.query, req.response, req.ground_truth)

@router.post("/batch")
async def batch_evaluate(req: BatchEvalRequest, request: Request):
    return await _svc(request).batch_evaluate(req.items)

@router.get("/metrics")
async def get_metrics(request: Request):
    return await _svc(request).get_metrics()
