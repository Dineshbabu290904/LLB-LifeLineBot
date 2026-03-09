"""Document Chunking Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/document-chunking", tags=["document-chunking"])

def _svc(request: Request):
    return request.app.state.service

class ChunkRequest(BaseModel):
    content: str
    doc_id: Optional[str] = None
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0, le=512)
    metadata: Optional[Dict[str, Any]] = None

class BatchChunkRequest(BaseModel):
    documents: List[Dict[str, Any]]

@router.post("/chunk")
async def chunk_document(req: ChunkRequest, request: Request):
    svc = _svc(request)
    return svc.chunk_document(req.content, req.doc_id, req.chunk_size, req.chunk_overlap, req.metadata)

@router.post("/batch")
async def batch_chunk(req: BatchChunkRequest, request: Request):
    svc = _svc(request)
    return svc.batch_chunk(req.documents)
