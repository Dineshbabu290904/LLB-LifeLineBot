from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from service import OrchestratorService

router = APIRouter()
orchestrator = OrchestratorService()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    image_data: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    patient_context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    conversation_id: str
    response: str
    triage_level: str
    is_emergency: bool
    doctor_recommendation: Optional[Dict[str, Any]]
    symptoms_identified: List[Dict[str, Any]]
    sources: List[str]
    hallucination_score: float
    safety_cleared: bool
    disclaimer: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — runs the full MEDBOT LangGraph pipeline."""
    session_id = request.session_id or str(uuid.uuid4())
    conversation_id = request.conversation_id or str(uuid.uuid4())

    result = await orchestrator.run_pipeline(
        user_query=request.message,
        session_id=session_id,
        conversation_id=conversation_id,
        image_data=request.image_data,
        conversation_history=request.conversation_history,
        patient_context=request.patient_context,
    )

    return ChatResponse(**{k: result[k] for k in ChatResponse.model_fields if k in result})


@router.get("/pipeline/info")
async def pipeline_info():
    """Return information about the pipeline graph."""
    return {
        "nodes": [
            "safety_input", "symptom_extraction", "vision_analysis",
            "rag_retrieval", "agentic_search", "knowledge_validation",
            "medical_reasoning", "hallucination_check", "triage",
            "doctor_recommendation", "safety_output",
            "dataset_generation", "evaluation",
        ],
        "description": "MEDBOT LangGraph Multi-Agent Medical Pipeline",
        "version": "1.0.0",
    }
