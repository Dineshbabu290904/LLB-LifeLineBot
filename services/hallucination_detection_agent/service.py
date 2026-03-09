"""
Hallucination Detection Agent

Approach (NLI-like without a heavy ML model):
1. Extract specific factual claims from the response using heuristics.
2. For each claim, compute token overlap with the retrieved context.
3. A claim is flagged as hallucinated when:
   - It contains specific medical facts (numbers, named conditions, drug names), AND
   - The overlap with the retrieved context is below the threshold.
"""
import re
import logging
from typing import List, Optional

logger = logging.getLogger("hallucination_detection_agent")

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "this", "that", "these", "those", "it", "its",
    "not", "no", "so", "if", "as", "also", "which", "who", "when", "where",
    "what", "how", "can", "you", "your", "we", "our", "they", "them",
    "patient", "patients",
}

# Patterns that mark a sentence as containing a specific medical claim
SPECIFIC_CLAIM_PATTERNS = [
    r"\b\d+\s*(?:mg|ml|mcg|mmol|iu|units?|tablets?|pills?|capsules?|doses?)\b",  # dosage
    r"\b(?:ibuprofen|acetaminophen|paracetamol|aspirin|metformin|atorvastatin|"
    r"lisinopril|omeprazole|amoxicillin|azithromycin|prednisone|warfarin|"
    r"metoprolol|amlodipine|simvastatin|levothyroxine|gabapentin|sertraline|"
    r"fluoxetine|clonazepam|lorazepam|alprazolam|oxycodone|hydrocodone)\b",       # drug names
    r"\b(?:diabetes|hypertension|asthma|copd|pneumonia|appendicitis|"
    r"myocardial infarction|atrial fibrillation|deep vein thrombosis|"
    r"pulmonary embolism|sepsis|meningitis|encephalitis|hepatitis|cirrhosis|"
    r"chronic kidney disease|heart failure|arrhythmia|angina)\b",                 # conditions
    r"\b(?:blood pressure|heart rate|glucose level|a1c|bmi|creatinine|"
    r"hemoglobin|white blood cell|platelet|troponin|d-dimer)\b",                  # lab values
    r"\b\d+\s*(?:%|percent)\s+(?:of|increase|decrease|risk|chance)\b",           # statistics
    r"\b(?:causes?|caused by|results? in|leads? to)\s+\w+",                      # causal claims
]
SPECIFIC_CLAIM_RE = re.compile("|".join(SPECIFIC_CLAIM_PATTERNS), re.IGNORECASE)

# Hedging phrases reduce hallucination risk
HEDGING_PATTERNS = [
    r"\b(according to|based on|as per|studies?\s+show|research\s+(shows?|suggests?)|"
    r"guidelines?\s+(recommend|state)|sources?\s+(indicate|suggest)|"
    r"evidence\s+suggests?|it\s+is\s+(generally|typically|commonly)\s+(accepted|known|recommended))\b"
]
HEDGING_RE = re.compile("|".join(HEDGING_PATTERNS), re.IGNORECASE)

OVERLAP_THRESHOLD = 0.30  # Minimum token overlap to consider a claim grounded


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return {t for t in tokens if t not in STOP_WORDS}


def extract_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def is_specific_claim(sentence: str) -> bool:
    return bool(SPECIFIC_CLAIM_RE.search(sentence))


def is_hedged(sentence: str) -> bool:
    return bool(HEDGING_RE.search(sentence))


def grounding_score(sentence: str, context_tokens: set[str]) -> float:
    """Token-overlap ratio between claim and context."""
    claim_tokens = tokenize(sentence)
    if not claim_tokens:
        return 1.0
    overlap = claim_tokens & context_tokens
    return len(overlap) / len(claim_tokens)


def analyze_claim(sentence: str, context_tokens: set[str]) -> dict:
    """Analyse a single sentence for hallucination risk."""
    specific = is_specific_claim(sentence)
    hedged = is_hedged(sentence)
    score = grounding_score(sentence, context_tokens)

    # Hallucinated = specific medical fact, not hedged, not grounded in context
    is_hallucinated = specific and not hedged and score < OVERLAP_THRESHOLD

    return {
        "claim": sentence,
        "is_specific": specific,
        "is_hedged": hedged,
        "grounding_score": round(score, 4),
        "is_hallucinated": is_hallucinated,
    }


class HallucinationDetectionService:
    def detect(
        self,
        response: str,
        retrieved_context: List[str],
        conversation_id: Optional[str] = None,
    ) -> dict:
        """
        Detect hallucinations in a response relative to the retrieved context.
        Returns full per-claim analysis.
        """
        if not response or not response.strip():
            return self._empty_result(conversation_id, "Empty response")

        combined_context = " ".join(retrieved_context) if retrieved_context else ""
        context_tokens = tokenize(combined_context)

        sentences = extract_sentences(response)
        if not sentences:
            return self._empty_result(conversation_id, "No analysable sentences")

        results: List[dict] = []
        for sent in sentences:
            results.append(analyze_claim(sent, context_tokens))

        hallucinated = [r for r in results if r["is_hallucinated"]]
        specific_claims = [r for r in results if r["is_specific"]]

        n_specific = len(specific_claims)
        n_hallucinated = len(hallucinated)
        hallucination_rate = n_hallucinated / n_specific if n_specific > 0 else 0.0

        flagged_claims = [r["claim"] for r in hallucinated]

        logger.info(
            "Hallucination detection — conv=%s sentences=%d specific=%d flagged=%d rate=%.3f",
            conversation_id, len(sentences), n_specific, n_hallucinated, hallucination_rate,
        )

        return {
            "conversation_id": conversation_id,
            "hallucination_rate": round(hallucination_rate, 4),
            "hallucination_results": results,
            "flagged_claims": flagged_claims,
            "total_sentences": len(sentences),
            "specific_claims_count": n_specific,
            "hallucinated_count": n_hallucinated,
        }

    def score(
        self,
        response: str,
        retrieved_context: List[str],
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Return just the hallucination rate and flagged claims (lighter endpoint)."""
        full = self.detect(response, retrieved_context, conversation_id)
        return {
            "conversation_id": conversation_id,
            "hallucination_rate": full.get("hallucination_rate", 0.0),
            "flagged_claims": full.get("flagged_claims", []),
            "hallucinated_count": full.get("hallucinated_count", 0),
            "specific_claims_count": full.get("specific_claims_count", 0),
        }

    @staticmethod
    def _empty_result(conversation_id: Optional[str], reason: str) -> dict:
        return {
            "conversation_id": conversation_id,
            "hallucination_rate": 0.0,
            "hallucination_results": [],
            "flagged_claims": [],
            "total_sentences": 0,
            "specific_claims_count": 0,
            "hallucinated_count": 0,
            "detail": reason,
        }
