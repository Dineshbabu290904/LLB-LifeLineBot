"""Metadata Storage Router."""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])

def _svc(request: Request):
    return request.app.state.service

class StoreRequest(BaseModel):
    entity_id: str
    metadata: Dict[str, Any]

@router.post("/store")
async def store(entity_type: str, req: StoreRequest, request: Request):
    return await _svc(request).store(entity_type, req.entity_id, req.metadata)

@router.get("/{entity_type}/{entity_id}")
async def get(entity_type: str, entity_id: str, request: Request):
    result = await _svc(request).get(entity_type, entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return result

@router.delete("/{entity_type}/{entity_id}")
async def delete(entity_type: str, entity_id: str, request: Request):
    return await _svc(request).delete(entity_type, entity_id)
