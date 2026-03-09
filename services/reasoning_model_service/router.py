"""
Reasoning Model Service - API route definitions.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from service import generate_reasoning, chat_reasoning

router = APIRouter(prefix="/api/v1/reasoning", tags=["reasoning"])


class PatientContext(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Medical query or reasoning task")
    patient_context: Optional[PatientContext] = Field(
        None, description="Patient demographic and medical context"
    )
    extra_context: Optional[str] = Field(
        None, description="Additional situational context (lab results, imaging notes, etc.)"
    )
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Lower = more deterministic")
    max_tokens: int = Field(2048, ge=1, le=8192)


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(
        ..., description="Ordered conversation history", min_length=1
    )
    patient_context: Optional[PatientContext] = Field(None)
    temperature: float = Field(0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(2048, ge=1, le=8192)


@router.post("/generate")
async def reasoning_generate(request: GenerateRequest):
    """
    Generate a medical reasoning response for the given prompt.
    Enriches the system prompt with patient context if provided.
    """
    try:
        patient_ctx = request.patient_context.model_dump() if request.patient_context else None
        result = await generate_reasoning(
            prompt=request.prompt,
            patient_context=patient_ctx,
            extra_context=request.extra_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Reasoning generation failed: {str(e)}")


@router.post("/chat")
async def reasoning_chat(request: ChatRequest):
    """
    Multi-turn medical reasoning conversation.
    Maintains context across the full message history.
    """
    try:
        messages = [m.model_dump() for m in request.messages]
        patient_ctx = request.patient_context.model_dump() if request.patient_context else None
        result = await chat_reasoning(
            messages=messages,
            patient_context=patient_ctx,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Chat reasoning failed: {str(e)}")
