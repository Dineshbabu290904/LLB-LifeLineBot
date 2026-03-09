from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from datetime import datetime
import uuid


class MedBotState(TypedDict, total=False):
    # Identifiers
    session_id: str
    conversation_id: str
    user_id: Optional[str]
    run_id: str

    # Input
    user_query: str
    image_data: Optional[str]
    patient_context: Dict[str, Any]

    # Conversation history
    conversation_history: List[Dict[str, str]]

    # Agent intermediate results
    extracted_symptoms: List[Dict[str, Any]]
    medical_entities: List[Dict[str, Any]]
    image_analysis: Optional[str]

    # RAG results
    retrieved_context: List[str]
    source_documents: List[Dict[str, Any]]
    search_queries_used: List[str]
    context_sufficient: bool

    # Reasoning
    medical_reasoning: str
    differential_diagnoses: List[str]

    # Triage and recommendation
    triage_level: str
    doctor_recommendation: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    is_emergency: bool

    # Safety
    input_safety_cleared: bool
    output_safety_cleared: bool
    safety_violations: List[str]

    # Hallucination detection
    hallucination_score: float
    hallucination_results: List[Dict[str, Any]]

    # Final output
    final_response: str
    sources: List[str]

    # Dataset and evaluation
    dataset_record: Optional[Dict[str, Any]]
    evaluation_report: Optional[Dict[str, Any]]

    # Control flow
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    pipeline_stage: str

    # Timing
    started_at: str
    completed_at: Optional[str]


def create_initial_state(
    user_query: str,
    session_id: str,
    conversation_id: str,
    image_data: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    patient_context: Optional[Dict[str, Any]] = None,
) -> MedBotState:
    return MedBotState(
        session_id=session_id,
        conversation_id=conversation_id,
        run_id=str(uuid.uuid4()),
        user_id=None,
        user_query=user_query,
        image_data=image_data,
        patient_context=patient_context or {},
        conversation_history=conversation_history or [],
        extracted_symptoms=[],
        medical_entities=[],
        image_analysis=None,
        retrieved_context=[],
        source_documents=[],
        search_queries_used=[],
        context_sufficient=False,
        medical_reasoning="",
        differential_diagnoses=[],
        triage_level="ROUTINE",
        doctor_recommendation=None,
        risk_assessment=None,
        is_emergency=False,
        input_safety_cleared=False,
        output_safety_cleared=False,
        safety_violations=[],
        hallucination_score=0.0,
        hallucination_results=[],
        final_response="",
        sources=[],
        dataset_record=None,
        evaluation_report=None,
        retry_count=0,
        max_retries=3,
        error_message=None,
        pipeline_stage="initialized",
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )
