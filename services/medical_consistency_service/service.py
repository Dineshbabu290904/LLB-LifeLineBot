import re
import logging
from typing import List

logger = logging.getLogger("medical_consistency_service")

# Stop-words to exclude from keyword matching
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our",
    "you", "your", "he", "she", "his", "her", "not", "no", "so", "if",
    "as", "also", "which", "who", "when", "where", "what", "how",
    "patient", "patients", "doctor", "physician", "medical", "medicine",
}

# Patterns that identify a "claim" sentence
CLAIM_INDICATORS = [
    r"\b(causes?|caused by|results? in|leads? to|associated with)\b",
    r"\b(treatment|treat|treated|therapy|dose|dosage|mg|ml|mcg)\b",
    r"\b(recommended|indicates?|suggests?|shows?|demonstrates?)\b",
    r"\b(effective|ineffective|contraindicated|safe|unsafe|dangerous)\b",
    r"\b(should|must|shall|do not|avoid|take|administer)\b",
    r"\b(symptom|sign|diagnosis|diagnose|prognosis|condition|disease|disorder)\b",
    r"\b\d+\s*(?:mg|ml|mcg|mmol|percent|%|days?|weeks?|hours?)\b",
]
CLAIM_PATTERN = re.compile("|".join(CLAIM_INDICATORS), re.IGNORECASE)


def tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text, excluding stop-words."""
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return {t for t in tokens if t not in STOP_WORDS}


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def is_claim_sentence(sentence: str) -> bool:
    """Determine whether a sentence makes a factual/medical claim."""
    return bool(CLAIM_PATTERN.search(sentence))


def sentence_supported_by_context(sentence: str, context_tokens: set[str], threshold: float = 0.35) -> bool:
    """
    Check if a response sentence is grounded in the retrieved context.
    Uses token-overlap Jaccard-like similarity.
    """
    sent_tokens = tokenize(sentence)
    if not sent_tokens:
        return True  # Empty sentence — not a claim
    overlap = sent_tokens & context_tokens
    overlap_ratio = len(overlap) / len(sent_tokens)
    return overlap_ratio >= threshold


class MedicalConsistencyService:
    def check(self, response: str, retrieved_sources: List[str], conversation_id: str | None = None) -> dict:
        """
        Check what fraction of factual claims in `response` are supported
        by the text in `retrieved_sources`.
        """
        if not response or not response.strip():
            return {
                "conversation_id": conversation_id,
                "consistency_score": 0.0,
                "supported_claims": [],
                "unsupported_claims": [],
                "total_claims": 0,
                "detail": "Empty response provided",
            }

        # Build a combined token set from all sources
        combined_context = " ".join(retrieved_sources) if retrieved_sources else ""
        context_tokens = tokenize(combined_context)

        sentences = extract_sentences(response)
        claim_sentences = [s for s in sentences if is_claim_sentence(s)]

        supported: List[str] = []
        unsupported: List[str] = []

        if not claim_sentences:
            # No explicit claims — conservatively score 0.5
            logger.info("No claim sentences found — assigning neutral consistency score")
            return {
                "conversation_id": conversation_id,
                "consistency_score": 0.5,
                "supported_claims": [],
                "unsupported_claims": [],
                "total_claims": 0,
                "detail": "No explicit factual claims detected in response",
            }

        for claim in claim_sentences:
            if not retrieved_sources:
                unsupported.append(claim)
            elif sentence_supported_by_context(claim, context_tokens):
                supported.append(claim)
            else:
                unsupported.append(claim)

        total = len(claim_sentences)
        score = len(supported) / total if total > 0 else 0.0

        logger.info(
            "Consistency check — conv=%s claims=%d supported=%d score=%.3f",
            conversation_id, total, len(supported), score,
        )

        return {
            "conversation_id": conversation_id,
            "consistency_score": round(score, 4),
            "supported_claims": supported,
            "unsupported_claims": unsupported,
            "total_claims": total,
            "detail": f"{len(supported)}/{total} claims supported by retrieved sources",
        }
