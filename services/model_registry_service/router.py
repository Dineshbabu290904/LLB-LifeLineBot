"""Model Registry Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/model-registry", tags=["model-registry"])

def _svc(request: Request):
    return request.app.state.service

class RegisterRequest(BaseModel):
    name: str
    capabilities: List[str]
    provider: str = "ollama"
    metadata: Dict[str, Any] = {}

@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    return await _svc(request).register(req.name, req.capabilities, req.provider, req.metadata)

@router.get("/models")
async def list_models(capability: Optional[str] = None, request: Request = None):
    return await _svc(request).list_models(capability)

@router.get("/models/{model_id}")
async def get_model(model_id: str, request: Request):
    model = await _svc(request).get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model
