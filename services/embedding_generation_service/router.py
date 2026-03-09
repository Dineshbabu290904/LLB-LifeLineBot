"""Embedding Generation Router."""
import logging
from typing import List
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/embedding-generation", tags=["embedding-generation"])

def _svc(request: Request):
    return request.app.state.service

class EmbedRequest(BaseModel):
    text: str
    model: str = "nomic-embed-text"

class BatchEmbedRequest(BaseModel):
    texts: List[str]
    model: str = "nomic-embed-text"

@router.post("/embed")
async def embed(req: EmbedRequest, request: Request):
    return await _svc(request).embed(req.text, req.model)

@router.post("/batch")
async def embed_batch(req: BatchEmbedRequest, request: Request):
    return await _svc(request).embed_batch(req.texts, req.model)
