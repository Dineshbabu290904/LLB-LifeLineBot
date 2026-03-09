from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from service import SafetyValidationService

router = APIRouter()
service = SafetyValidationService()


class SafetyValidateRequest(BaseModel):
    response: str = Field(..., description="Medical response to validate")
    query: str = Field(default="", description="Original user query")
    triage_level: str = Field(default="NON_URGENT", description="Assigned triage level")
    conversation_id: Optional[str] = None


class SafetyValidateResponse(BaseModel):
    conversation_id: Optional[str]
    overall_score: float
    checks: Dict[str, bool]
    issues: List[str]
    flagged_advice: List[str]
    pii_found: List[str]
    is_safe: bool


@router.post("/safety/validate", response_model=SafetyValidateResponse)
async def validate_safety(request: SafetyValidateRequest):
    """
    Validate a medical response for safety compliance.
    Checks: disclaimer present, emergency handled, no dangerous advice, PII-free.
    """
    result = service.validate(
        response=request.response,
        query=request.query,
        triage_level=request.triage_level,
        conversation_id=request.conversation_id,
    )
    return result
