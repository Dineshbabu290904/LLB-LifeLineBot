"""Document Ingestion Service - full pipeline: ingest -> clean -> chunk -> embed -> store."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    cleaning_url: str = "http://document_cleaning_service:8062"
    chunking_url: str = "http://document_chunking_service:8061"
    embedding_url: str = "http://embedding_generation_service:8054"
    vector_index_url: str = "http://vector_index_service:8055"
    request_timeout: int = 60
    class Config:
        env_prefix = "DOC_INGEST_"

settings = Settings()


class DocumentIngestionService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._docs: Dict[str, Dict[str, Any]] = {}

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        logger.info("DocumentIngestionService started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Not started")
        return self._client

    async def _call(self, method: str, url: str, json_body: Any = None) -> Dict[str, Any]:
        try:
            resp = await self.client.request(method, url, json=json_body)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Call to %s failed: %s", url, exc)
            return {"error": str(exc)}

    async def ingest(
        self,
        content: str,
        source: Optional[str] = None,
        doc_type: str = "medical_document",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        doc_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        self._docs[doc_id] = {"status": "processing", "created_at": created_at}

        pipeline_steps = []

        # Step 1: Clean
        clean_result = await self._call(
            "POST",
            f"{settings.cleaning_url}/api/v1/document-cleaning/clean",
            {"content": content, "doc_id": doc_id},
        )
        pipeline_steps.append({"step": "cleaning", "success": "error" not in clean_result})
        cleaned_content = clean_result.get("cleaned_content", content)

        # Step 2: Chunk
        chunk_result = await self._call(
            "POST",
            f"{settings.chunking_url}/api/v1/document-chunking/chunk",
            {"content": cleaned_content, "doc_id": doc_id, "metadata": metadata or {}},
        )
        pipeline_steps.append({"step": "chunking", "success": "error" not in chunk_result})
        chunks = chunk_result.get("chunks", [])

        # Step 3: Embed
        embed_result = await self._call(
            "POST",
            f"{settings.embedding_url}/api/v1/embedding-generation/batch",
            {"texts": [c["content"] for c in chunks], "doc_id": doc_id},
        )
        pipeline_steps.append({"step": "embedding", "success": "error" not in embed_result})

        self._docs[doc_id] = {
            "status": "completed",
            "created_at": created_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "chunks_count": len(chunks),
            "source": source,
            "doc_type": doc_type,
        }

        return {
            "doc_id": doc_id,
            "status": "completed",
            "chunks_created": len(chunks),
            "pipeline_steps": pipeline_steps,
            "source": source,
        }

    def get_status(self, doc_id: str) -> Dict[str, Any]:
        doc = self._docs.get(doc_id)
        if not doc:
            return {"error": "Document not found"}
        return {"doc_id": doc_id, **doc}
