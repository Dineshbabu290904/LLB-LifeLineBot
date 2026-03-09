"""Document Chunking Service - chunks medical documents into retrievable segments."""
import logging
import uuid
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    chunk_size: int = 512
    chunk_overlap: int = 64
    class Config:
        env_prefix = "CHUNKING_"

settings = Settings()


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at sentence boundary
        if end < len(text):
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                idx = text.rfind(sep, start, end)
                if idx > start:
                    end = idx + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = max(start + 1, end - overlap)
    return [c for c in chunks if c]


class DocumentChunkingService:
    async def startup(self):
        logger.info("DocumentChunkingService started")

    async def shutdown(self):
        pass

    def chunk_document(
        self,
        content: str,
        doc_id: Optional[str] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        doc_id = doc_id or str(uuid.uuid4())
        chunks_text = _split_text(content, chunk_size, chunk_overlap)
        chunks = [
            {
                "chunk_id": f"{doc_id}_chunk_{i}",
                "doc_id": doc_id,
                "content": chunk,
                "position": i,
                "char_count": len(chunk),
                "metadata": metadata or {},
            }
            for i, chunk in enumerate(chunks_text)
        ]
        return {
            "doc_id": doc_id,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "total_chars": len(content),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }

    def batch_chunk(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for doc in documents:
            result = self.chunk_document(
                content=doc.get("content", ""),
                doc_id=doc.get("doc_id"),
                chunk_size=doc.get("chunk_size", settings.chunk_size),
                chunk_overlap=doc.get("chunk_overlap", settings.chunk_overlap),
                metadata=doc.get("metadata"),
            )
            results.append(result)
        total_chunks = sum(r["total_chunks"] for r in results)
        return {"results": results, "documents_processed": len(results), "total_chunks": total_chunks}
