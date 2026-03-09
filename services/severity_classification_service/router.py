from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from service import classify_severity, SeverityResult

router = APIRouter(prefix="/api/v1/severity", tags=["severity"])


class ClassifyRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1, description="List of symptom names or descriptions")
    patient_history: Optional[str] = Field(default=None, description="Relevant patient medical history")
    duration: Optional[str] = Field(default=None, description="Duration of symptoms (e.g., '2 hours', '3 days')")
    onset: Optional[str] = Field(default=None, description="Onset description (e.g., 'sudden', 'gradual')")
    use_llm: bool = Field(default=True, description="Whether to use LLM augmentation")


class ScoreRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    patient_history: Optional[str] = None
    duration: Optional[str] = None
    onset: Optional[str] = None
    use_llm: bool = True


class ScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Numeric severity score 0-100")
    severity_level: str
    factors: List[str]


@router.post("/classify", response_model=SeverityResult)
async def classify_severity_endpoint(request: ClassifyRequest):
    """
    Classify symptom severity into mild/moderate/severe/critical.
    Considers symptom types, duration, onset speed, and patient history.
    """
    if not request.symptoms:
        raise HTTPException(status_code=422, detail="At least one symptom is required.")

    return await classify_severity(
        symptoms=request.symptoms,
        patient_history=request.patient_history,
        duration=request.duration,
        onset=request.onset,
        use_llm=request.use_llm,
    )


@router.post("/score", response_model=ScoreResponse)
async def get_severity_score(request: ScoreRequest):
    """
    Get a numeric severity score from 0-100 for a list of symptoms.
    0 = asymptomatic, 100 = life-threatening emergency.
    """
    if not request.symptoms:
        raise HTTPException(status_code=422, detail="At least one symptom is required.")

    result = await classify_severity(
        symptoms=request.symptoms,
        patient_history=request.patient_history,
        duration=request.duration,
        onset=request.onset,
        use_llm=request.use_llm,
    )

    return ScoreResponse(
        score=result.score,
        severity_level=result.severity_level,
        factors=result.factors,
    )
