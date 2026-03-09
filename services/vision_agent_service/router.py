"""Vision Agent Router."""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/vision-agent", tags=["vision-agent"])

def _svc(request: Request):
    return request.app.state.service

class AnalyzeRequest(BaseModel):
    image_data: str  # base64 encoded image
    image_type: str = "xray"
    query: str = "Describe what you see in this medical image."

class DescribeRequest(BaseModel):
    image_data: str
    findings_type: str = "general"

@router.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    return await _svc(request).analyze(req.image_data, req.image_type, req.query)

@router.post("/describe")
async def describe(req: DescribeRequest, request: Request):
    return await _svc(request).describe(req.image_data, req.findings_type)
