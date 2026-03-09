from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
from service import HallucinationDetectionService

router = APIRouter()
service = HallucinationDetectionService()


class HallucinationRequest(BaseModel):
    response: str = Field(..., description="Medical response to analyse")
    retrieved_context: List[str] = Field(default_factory=list, description="Source texts used to generate the response")
    conversation_id: Optional[str] = None


class HallucinationDetectResponse(BaseModel):
    conversation_id: Optional[str]
    hallucination_rate: float
    hallucination_results: List[dict]
    flagged_claims: List[str]
    total_sentences: int
    specific_claims_count: int
    hallucinated_count: int


class HallucinationScoreResponse(BaseModel):
    conversation_id: Optional[str]
    hallucination_rate: float
    flagged_claims: List[str]
    hallucinated_count: int
    specific_claims_count: int


@router.post("/hallucination/detect", response_model=HallucinationDetectResponse)
async def detect_hallucinations(request: HallucinationRequest):
    """
    Detect hallucinations in a response by comparing specific medical claims
    against the retrieved context using NLI-like token grounding analysis.
    """
    result = service.detect(
        response=request.response,
        retrieved_context=request.retrieved_context,
        conversation_id=request.conversation_id,
    )
    return result


@router.post("/hallucination/score", response_model=HallucinationScoreResponse)
async def get_hallucination_score(request: HallucinationRequest):
    """Return a lightweight hallucination score without full per-claim breakdown."""
    result = service.score(
        response=request.response,
        retrieved_context=request.retrieved_context,
        conversation_id=request.conversation_id,
    )
    return result
