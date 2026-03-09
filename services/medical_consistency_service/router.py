from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from service import MedicalConsistencyService

router = APIRouter()
service = MedicalConsistencyService()


class ConsistencyCheckRequest(BaseModel):
    response: str = Field(..., description="Medical response text to evaluate")
    retrieved_sources: List[str] = Field(default_factory=list, description="Source texts used for grounding")
    conversation_id: Optional[str] = None


class ConsistencyCheckResponse(BaseModel):
    conversation_id: Optional[str]
    consistency_score: float
    supported_claims: List[str]
    unsupported_claims: List[str]
    total_claims: int
    detail: str


@router.post("/consistency/check", response_model=ConsistencyCheckResponse)
async def check_consistency(request: ConsistencyCheckRequest):
    """
    Check what fraction of factual/medical claims in a response are
    supported by the provided retrieved source texts.
    """
    result = service.check(
        response=request.response,
        retrieved_sources=request.retrieved_sources,
        conversation_id=request.conversation_id,
    )
    return result
