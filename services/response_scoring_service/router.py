import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/response-scoring", tags=["response-scoring"])


class ScoreRequest(BaseModel):
    conversation_id: str
    query: str
    response: str
    retrieved_sources: List[str] = []
    triage_level: str = "ROUTINE"


class ScoreResponse(BaseModel):
    conversation_id: str
    composite_score: float
    requires_retraining: bool
    component_scores: dict
    weights: dict
    retrain_threshold: float
    evaluated_at: str


def _svc(request: Request):
    return request.app.state.service


@router.post("/score", response_model=ScoreResponse)
async def score_response(payload: ScoreRequest, request: Request):
    """Score an LLM response using all sub-scoring services."""
    try:
        svc = _svc(request)
        result = await svc.score_response(
            conversation_id=payload.conversation_id,
            query=payload.query,
            response=payload.response,
            retrieved_sources=payload.retrieved_sources,
            triage_level=payload.triage_level,
        )
        return result
    except Exception as exc:
        logger.error("Scoring error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/thresholds")
async def get_thresholds():
    """Return scoring thresholds and weights."""
    from service import W_TRIAGE, W_CONSISTENCY, W_HALLUCINATION, W_SAFETY, W_GROUNDING, RETRAIN_THRESHOLD
    return {
        "retrain_threshold": RETRAIN_THRESHOLD,
        "weights": {
            "triage_accuracy": W_TRIAGE,
            "medical_consistency": W_CONSISTENCY,
            "hallucination_inverted": W_HALLUCINATION,
            "safety": W_SAFETY,
            "grounding": W_GROUNDING,
        },
    }
