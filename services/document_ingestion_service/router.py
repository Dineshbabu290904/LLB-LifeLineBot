"""Document Ingestion Router."""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/document-ingestion", tags=["document-ingestion"])

def _svc(request: Request):
    return request.app.state.service

class IngestRequest(BaseModel):
    content: str
    source: Optional[str] = None
    doc_type: str = "medical_document"
    metadata: Optional[Dict[str, Any]] = None

@router.post("/ingest")
async def ingest_document(req: IngestRequest, request: Request):
    svc = _svc(request)
    return await svc.ingest(req.content, req.source, req.doc_type, req.metadata)

@router.get("/status/{doc_id}")
async def get_status(doc_id: str, request: Request):
    svc = _svc(request)
    result = svc.get_status(doc_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
