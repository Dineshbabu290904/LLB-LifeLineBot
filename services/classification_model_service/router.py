import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/classification", tags=["classification"])


class TriageRequest(BaseModel):
    symptoms: str
    patient_age: Optional[int] = None
    patient_context: Optional[str] = None


class SeverityRequest(BaseModel):
    symptoms: str
    pain_scale: Optional[int] = None


class TriageResponse(BaseModel):
    triage_level: str
    confidence: float
    reasoning: str
    red_flags: list
    method: str
    patient_age: Optional[int] = None


class SeverityResponse(BaseModel):
    severity_level: str
    severity_score: int
    confidence: float
    method: str
    reasoning: str


@router.post("/triage", response_model=TriageResponse)
async def classify_triage(payload: TriageRequest, request: Request):
    """Classify patient triage level from symptoms."""
    try:
        from service import triage_classify
        result = await triage_classify(
            symptoms=payload.symptoms,
            patient_age=payload.patient_age,
            patient_context=payload.patient_context,
        )
        return result
    except Exception as exc:
        logger.error("Triage classification error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/severity", response_model=SeverityResponse)
async def classify_severity(payload: SeverityRequest, request: Request):
    """Classify symptom severity level."""
    try:
        from service import classify_severity
        result = await classify_severity(
            symptoms=payload.symptoms,
            pain_scale=payload.pain_scale,
        )
        return result
    except Exception as exc:
        logger.error("Severity classification error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/levels")
async def get_triage_levels():
    """Return available triage and severity levels."""
    from service import TRIAGE_LEVELS, SEVERITY_LEVELS
    return {
        "triage_levels": TRIAGE_LEVELS,
        "severity_levels": list(SEVERITY_LEVELS.keys()),
    }
