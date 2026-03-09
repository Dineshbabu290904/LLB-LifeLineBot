"""Model Versioning Router."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/model-versioning", tags=["model-versioning"])

def _svc(request: Request):
    return request.app.state.service

class CreateVersionRequest(BaseModel):
    model_id: str
    version_tag: str
    config: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}

@router.post("/version")
async def create_version(req: CreateVersionRequest, request: Request):
    return await _svc(request).create_version(req.model_id, req.version_tag, req.config, req.metrics)

@router.get("/versions/{model_id}")
async def list_versions(model_id: str, request: Request):
    return await _svc(request).list_versions(model_id)

@router.post("/promote/{version_id}")
async def promote(version_id: str, request: Request):
    return await _svc(request).promote(version_id)
