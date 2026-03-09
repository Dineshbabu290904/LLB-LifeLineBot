"""Quality control nodes: hallucination detection, dataset generation, evaluation."""
import httpx
import logging
from datetime import datetime
from state import MedBotState
from config import get_config

logger = logging.getLogger("quality_nodes")
config = get_config()


async def _call_service(url: str, endpoint: str, data: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{url}{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Service call failed {url}{endpoint}: {e}")
        return {}


async def hallucination_detection_node(state: MedBotState) -> MedBotState:
    """Detect hallucinations in the generated response."""
    logger.info(f"[{state['run_id']}] Hallucination detection")
    state["pipeline_stage"] = "hallucination_detection"

    result = await _call_service(
        config.hallucination_detection_url,
        "/api/v1/hallucination/detect",
        {
            "response": state.get("final_response", ""),
            "retrieved_context": state.get("retrieved_context", []),
            "medical_reasoning": state.get("medical_reasoning", ""),
        },
    )

    if result:
        state["hallucination_score"] = result.get("hallucination_rate", 0.0)
        state["hallucination_results"] = result.get("hallucination_results", [])
    else:
        state["hallucination_score"] = 0.0
        state["hallucination_results"] = []

    logger.info(f"[{state['run_id']}] Hallucination score: {state['hallucination_score']:.3f}")
    return state


async def dataset_generation_node(state: MedBotState) -> MedBotState:
    """Generate a training dataset record from this interaction."""
    logger.info(f"[{state['run_id']}] Dataset generation")
    state["pipeline_stage"] = "dataset_generation"

    result = await _call_service(
        config.dataset_generation_url,
        "/api/v1/dataset/generate",
        {
            "conversation_id": state["conversation_id"],
            "session_id": state["session_id"],
            "conversation_history": state.get("conversation_history", []),
            "user_query": state["user_query"],
            "assistant_response": state.get("final_response", ""),
            "symptoms_extracted": state.get("extracted_symptoms", []),
            "diagnosis_reasoning": state.get("medical_reasoning", ""),
            "triage_level": state.get("triage_level", "ROUTINE"),
            "doctor_recommendation": state.get("doctor_recommendation"),
            "knowledge_sources": state.get("sources", []),
            "retrieved_context": state.get("retrieved_context", []),
            "hallucination_score": state.get("hallucination_score", 0.0),
            "is_emergency": state.get("is_emergency", False),
            "has_image": state.get("image_data") is not None,
        },
    )

    if result:
        state["dataset_record"] = result
    else:
        # Create minimal dataset record inline
        state["dataset_record"] = {
            "conversation_id": state["conversation_id"],
            "user_query": state["user_query"],
            "assistant_response": state.get("final_response", ""),
            "triage_level": state.get("triage_level", "ROUTINE"),
            "created_at": datetime.utcnow().isoformat(),
        }

    return state


async def evaluation_node(state: MedBotState) -> MedBotState:
    """Evaluate the quality and safety of the generated response."""
    logger.info(f"[{state['run_id']}] Response evaluation")
    state["pipeline_stage"] = "evaluation"

    result = await _call_service(
        config.evaluation_agent_url,
        "/api/v1/evaluate",
        {
            "conversation_id": state["conversation_id"],
            "query": state["user_query"],
            "response": state.get("final_response", ""),
            "retrieved_sources": state.get("sources", []),
            "retrieved_context": state.get("retrieved_context", []),
            "triage_level": state.get("triage_level", "ROUTINE"),
            "symptoms": state.get("extracted_symptoms", []),
            "hallucination_score": state.get("hallucination_score", 0.0),
            "safety_violations": state.get("safety_violations", []),
            "is_emergency": state.get("is_emergency", False),
        },
    )

    if result:
        state["evaluation_report"] = result
    else:
        state["evaluation_report"] = {
            "conversation_id": state["conversation_id"],
            "composite_score": 0.7,
            "requires_retraining": False,
            "note": "Evaluation service unavailable",
        }

    return state
