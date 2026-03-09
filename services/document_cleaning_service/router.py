"""Document Cleaning Router."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/document-cleaning", tags=["document-cleaning"])

def _svc(request: Request):
    return request.app.state.service

class CleanRequest(BaseModel):
    content: str
    doc_id: Optional[str] = None
    remove_headers: bool = False
    normalize_whitespace: bool = True

class BatchCleanRequest(BaseModel):
    documents: List[Dict[str, Any]]

@router.post("/clean")
async def clean_document(req: CleanRequest, request: Request):
    svc = _svc(request)
    return svc.clean_document(req.content, req.doc_id, req.remove_headers, req.normalize_whitespace)

@router.post("/batch")
async def batch_clean(req: BatchCleanRequest, request: Request):
    svc = _svc(request)
    return svc.batch_clean(req.documents)
