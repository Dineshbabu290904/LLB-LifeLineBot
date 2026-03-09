from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from service import TriageAccuracyService

router = APIRouter()
service = TriageAccuracyService()


class TriageValidateRequest(BaseModel):
    symptoms: str = Field(..., description="Patient symptom description")
    actual_level: str = Field(..., description="Triage level assigned by the system")
    conversation_id: Optional[str] = None


class TriageValidateResponse(BaseModel):
    conversation_id: Optional[str]
    is_accurate: bool
    expected_level: str
    actual_level: str
    accuracy_score: float
    reasoning: str


class BatchRecord(BaseModel):
    symptoms: str
    actual_level: str
    conversation_id: Optional[str] = None


class BatchAccuracyRequest(BaseModel):
    records: List[BatchRecord] = Field(..., min_length=1)


class BatchAccuracyResponse(BaseModel):
    total: int
    valid: int
    mean_accuracy: float
    level_breakdown: dict
    results: List[dict]


@router.post("/triage/validate", response_model=TriageValidateResponse)
async def validate_triage(request: TriageValidateRequest):
    """Validate a single triage decision against symptom analysis."""
    result = service.validate(
        symptoms=request.symptoms,
        actual_level=request.actual_level,
        conversation_id=request.conversation_id,
    )
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.post("/triage/accuracy", response_model=BatchAccuracyResponse)
async def compute_batch_accuracy(request: BatchAccuracyRequest):
    """Compute triage accuracy over a batch of records."""
    records = [r.model_dump() for r in request.records]
    result = service.compute_batch_accuracy(records)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result
