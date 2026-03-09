"""Document Cleaning Service - cleans and preprocesses medical documents."""
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    class Config:
        env_prefix = "DOC_CLEAN_"

settings = Settings()


def _clean_text(text: str) -> str:
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove control characters except newlines
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', text)
    # Normalize dashes and quotes
    text = text.replace('\u2013', '-').replace('\u2014', '--')
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    # Remove repeated punctuation
    text = re.sub(r'([.!?]){3,}', r'\1\1\1', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def _extract_metadata(text: str) -> Dict[str, Any]:
    word_count = len(text.split())
    sentence_count = len(re.findall(r'[.!?]+', text))
    has_medical_terms = bool(re.search(
        r'\b(diagnosis|treatment|symptom|patient|clinical|medical|disease|condition|therapy)\b',
        text, re.IGNORECASE
    ))
    return {
        "word_count": word_count,
        "char_count": len(text),
        "sentence_count": sentence_count,
        "has_medical_terms": has_medical_terms,
    }


class DocumentCleaningService:
    async def startup(self):
        logger.info("DocumentCleaningService started")

    async def shutdown(self):
        pass

    def clean_document(
        self,
        content: str,
        doc_id: Optional[str] = None,
        remove_headers: bool = False,
        normalize_whitespace: bool = True,
    ) -> Dict[str, Any]:
        original_length = len(content)
        cleaned = _clean_text(content)

        if remove_headers:
            # Remove common header/footer patterns
            cleaned = re.sub(r'^(Page \d+|CONFIDENTIAL|DRAFT).*$', '', cleaned, flags=re.MULTILINE)

        meta = _extract_metadata(cleaned)
        return {
            "doc_id": doc_id,
            "cleaned_content": cleaned,
            "original_length": original_length,
            "cleaned_length": len(cleaned),
            "reduction_pct": round((1 - len(cleaned) / max(original_length, 1)) * 100, 2),
            "metadata": meta,
        }

    def batch_clean(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for doc in documents:
            result = self.clean_document(
                content=doc.get("content", ""),
                doc_id=doc.get("doc_id"),
                remove_headers=doc.get("remove_headers", False),
                normalize_whitespace=doc.get("normalize_whitespace", True),
            )
            results.append(result)
        return {"results": results, "documents_processed": len(results)}
