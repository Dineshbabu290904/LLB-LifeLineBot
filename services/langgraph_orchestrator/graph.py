"""
MEDBOT LangGraph Pipeline

Full agent graph:
  START
    → safety_input
    ↓ (safe) or END (unsafe)
    → symptom_extraction
    ↓
    → vision_analysis (if image)
    ↓
    → rag_retrieval
    ↓ (insufficient?) → agentic_search → knowledge_validation
    ↓
    → medical_reasoning
    ↓
    → hallucination_check
    ↓ (score>0.3 and retries left?) → medical_reasoning (retry)
    ↓
    → triage
    ↓
    → doctor_recommendation
    ↓
    → safety_output
    ↓
    → dataset_generation
    ↓
    → evaluation
    → END
"""
from langgraph.graph import StateGraph, END
from state import MedBotState
from nodes import (
    safety_input_node,
    safety_output_node,
    symptom_extraction_node,
    vision_analysis_node,
    rag_retrieval_node,
    agentic_search_node,
    knowledge_validation_node,
    medical_reasoning_node,
    hallucination_detection_node,
    triage_node,
    doctor_recommendation_node,
    dataset_generation_node,
    evaluation_node,
)
import logging

logger = logging.getLogger("medbot_graph")


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_after_safety_input(state: MedBotState) -> str:
    """Route after input safety check."""
    if not state.get("input_safety_cleared"):
        logger.warning(f"[{state['run_id']}] Input blocked by safety guardrail")
        return "blocked"
    if state.get("is_emergency"):
        # Emergency: still extract symptoms but fast-track triage
        return "symptom_extraction"
    return "symptom_extraction"


def route_after_symptom_extraction(state: MedBotState) -> str:
    """Route based on whether image is present."""
    if state.get("image_data"):
        return "vision_analysis"
    return "rag_retrieval"


def route_after_vision_analysis(state: MedBotState) -> str:
    return "rag_retrieval"


def route_after_rag_retrieval(state: MedBotState) -> str:
    """If context is insufficient, do agentic search."""
    if not state.get("context_sufficient") and not state.get("is_emergency"):
        return "agentic_search"
    return "medical_reasoning"


def route_after_search(state: MedBotState) -> str:
    return "knowledge_validation"


def route_after_knowledge_validation(state: MedBotState) -> str:
    return "medical_reasoning"


def route_after_hallucination_check(state: MedBotState) -> str:
    """Retry reasoning if hallucination is high and retries remain."""
    score = state.get("hallucination_score", 0.0)
    retry = state.get("retry_count", 0)
    max_r = state.get("max_retries", 3)

    if score > 0.5 and retry < max_r:
        state["retry_count"] = retry + 1
        logger.info(f"[{state['run_id']}] Retrying reasoning (attempt {retry + 1})")
        return "medical_reasoning"
    return "triage"


def create_emergency_response(state: MedBotState) -> MedBotState:
    """Fast emergency response node."""
    state["final_response"] = (
        "⚠️ EMERGENCY ALERT: Based on the symptoms you described, this appears to be "
        "a potential medical emergency. Please take immediate action:\n\n"
        "1. Call 911 (or your local emergency number) immediately\n"
        "2. Go to the nearest emergency room\n"
        "3. If possible, have someone stay with you\n"
        "4. Do not drive yourself\n\n"
        "Do not delay seeking emergency medical care for any reason."
    )
    state["triage_level"] = "EMERGENCY"
    state["output_safety_cleared"] = True
    return state


def create_blocked_response(state: MedBotState) -> MedBotState:
    """Response when input is blocked by safety."""
    state["final_response"] = (
        "I'm unable to process this request due to safety concerns. "
        "Please rephrase your medical question clearly and try again. "
        "If you have a medical emergency, call 911 immediately.\n\n"
        "⚠️ MEDICAL DISCLAIMER: This system is for educational purposes only. "
        "Always consult a qualified healthcare professional."
    )
    state["output_safety_cleared"] = True
    return state


# ─── Graph Builder ────────────────────────────────────────────────────────────

def build_medbot_graph():
    """Build and compile the full MEDBOT LangGraph pipeline."""
    workflow = StateGraph(MedBotState)

    # Add all processing nodes
    workflow.add_node("safety_input", safety_input_node)
    workflow.add_node("symptom_extraction", symptom_extraction_node)
    workflow.add_node("vision_analysis", vision_analysis_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("agentic_search", agentic_search_node)
    workflow.add_node("knowledge_validation", knowledge_validation_node)
    workflow.add_node("medical_reasoning", medical_reasoning_node)
    workflow.add_node("hallucination_check", hallucination_detection_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("doctor_recommendation", doctor_recommendation_node)
    workflow.add_node("safety_output", safety_output_node)
    workflow.add_node("dataset_generation", dataset_generation_node)
    workflow.add_node("evaluation", evaluation_node)

    # Control flow nodes
    workflow.add_node("blocked_response", create_blocked_response)

    # Set entry point
    workflow.set_entry_point("safety_input")

    # Add conditional and direct edges
    workflow.add_conditional_edges(
        "safety_input",
        route_after_safety_input,
        {
            "symptom_extraction": "symptom_extraction",
            "blocked": "blocked_response",
        },
    )

    workflow.add_conditional_edges(
        "symptom_extraction",
        route_after_symptom_extraction,
        {
            "vision_analysis": "vision_analysis",
            "rag_retrieval": "rag_retrieval",
        },
    )

    workflow.add_edge("vision_analysis", "rag_retrieval")

    workflow.add_conditional_edges(
        "rag_retrieval",
        route_after_rag_retrieval,
        {
            "agentic_search": "agentic_search",
            "medical_reasoning": "medical_reasoning",
        },
    )

    workflow.add_edge("agentic_search", "knowledge_validation")
    workflow.add_edge("knowledge_validation", "medical_reasoning")

    workflow.add_edge("medical_reasoning", "hallucination_check")

    workflow.add_conditional_edges(
        "hallucination_check",
        route_after_hallucination_check,
        {
            "medical_reasoning": "medical_reasoning",
            "triage": "triage",
        },
    )

    workflow.add_edge("triage", "doctor_recommendation")
    workflow.add_edge("doctor_recommendation", "safety_output")
    workflow.add_edge("safety_output", "dataset_generation")
    workflow.add_edge("dataset_generation", "evaluation")
    workflow.add_edge("evaluation", END)
    workflow.add_edge("blocked_response", END)

    return workflow.compile()


# Singleton compiled graph
_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_medbot_graph()
        logger.info("MedBot LangGraph compiled successfully")
    return _compiled_graph
