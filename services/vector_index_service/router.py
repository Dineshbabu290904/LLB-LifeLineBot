"""Vector Index Router."""
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/vector-index", tags=["vector-index"])

def _svc(request: Request):
    return request.app.state.service

class CreateIndexRequest(BaseModel):
    name: str
    dimension: int
    metric: str = "cosine"

class AddVectorsRequest(BaseModel):
    vectors: List[Dict[str, Any]]

@router.post("/create")
async def create_index(req: CreateIndexRequest, request: Request):
    return await _svc(request).create_index(req.name, req.dimension, req.metric)

@router.delete("/{index_id}")
async def delete_index(index_id: str, request: Request):
    return await _svc(request).delete_index(index_id)

@router.post("/{index_id}/add")
async def add_vectors(index_id: str, req: AddVectorsRequest, request: Request):
    return await _svc(request).add_vectors(index_id, req.vectors)

@router.get("/")
async def list_indices(request: Request):
    return await _svc(request).list_indices()
