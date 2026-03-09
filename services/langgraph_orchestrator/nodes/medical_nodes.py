"""Medical processing nodes: symptom extraction, reasoning, triage, doctor recommendation."""
import httpx
import logging
from typing import Optional
from state import MedBotState
from config import get_config

logger = logging.getLogger("medical_nodes")
config = get_config()


async def _call_service(url: str, endpoint: str, data: dict) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{url}{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Service call failed {url}{endpoint}: {e}")
        return None


async def symptom_extraction_node(state: MedBotState) -> MedBotState:
    """Extract symptoms and medical entities from the user query."""
    logger.info(f"[{state['run_id']}] Extracting symptoms")
    state["pipeline_stage"] = "symptom_extraction"

    result = await _call_service(
        config.symptom_extraction_url,
        "/api/v1/extract/symptoms",
        {
            "text": state["user_query"],
            "conversation_history": state.get("conversation_history", []),
            "patient_context": state.get("patient_context", {}),
        },
    )

    if result:
        state["extracted_symptoms"] = result.get("symptoms", [])
        state["medical_entities"] = result.get("entities", [])
    else:
        # Fallback: basic keyword extraction
        state["extracted_symptoms"] = [{"name": state["user_query"][:100], "severity": "unknown"}]
        state["medical_entities"] = []

    logger.info(f"[{state['run_id']}] Extracted {len(state['extracted_symptoms'])} symptoms")
    return state


async def vision_analysis_node(state: MedBotState) -> MedBotState:
    """Analyze medical image if provided."""
    logger.info(f"[{state['run_id']}] Analyzing image")
    state["pipeline_stage"] = "vision_analysis"

    if not state.get("image_data"):
        return state

    result = await _call_service(
        config.vision_agent_url,
        "/api/v1/vision/analyze",
        {
            "image_data": state["image_data"],
            "query": state["user_query"],
            "symptoms_context": state.get("extracted_symptoms", []),
        },
    )

    if result:
        state["image_analysis"] = result.get("description", "")
        # Add image findings to symptoms
        visual_findings = result.get("visual_findings", [])
        for finding in visual_findings:
            state["extracted_symptoms"].append({
                "name": finding,
                "severity": "unknown",
                "source": "image_analysis",
            })

    return state


async def medical_reasoning_node(state: MedBotState) -> MedBotState:
    """Generate medical reasoning from symptoms + retrieved context."""
    logger.info(f"[{state['run_id']}] Medical reasoning (retry={state.get('retry_count', 0)})")
    state["pipeline_stage"] = "medical_reasoning"

    context_parts = state.get("retrieved_context", [])
    context_text = "\n\n---\n\n".join(context_parts[:5]) if context_parts else "No specific sources retrieved."

    symptoms_text = ", ".join(
        s.get("name", "") for s in state.get("extracted_symptoms", [])
    ) or state["user_query"]

    image_note = ""
    if state.get("image_analysis"):
        image_note = f"\n\nImage Analysis: {state['image_analysis']}"

    history_text = ""
    if state.get("conversation_history"):
        recent = state["conversation_history"][-4:]
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent)

    result = await _call_service(
        config.reasoning_agent_url,
        "/api/v1/reasoning/medical",
        {
            "query": state["user_query"],
            "symptoms": state.get("extracted_symptoms", []),
            "medical_context": context_text,
            "image_analysis": state.get("image_analysis"),
            "conversation_history": history_text,
            "patient_context": state.get("patient_context", {}),
        },
    )

    if result:
        state["medical_reasoning"] = result.get("reasoning", "")
        state["final_response"] = result.get("response", "")
        state["differential_diagnoses"] = result.get("differential_diagnoses", [])
        state["sources"] = result.get("sources_used", []) + [
            doc.get("url", "") for doc in state.get("source_documents", [])
        ]
    else:
        # Fallback response
        state["medical_reasoning"] = f"Based on symptoms: {symptoms_text}"
        state["final_response"] = (
            f"Based on the symptoms you've described ({symptoms_text}), "
            f"I recommend consulting a healthcare professional for a proper evaluation."
        )

    return state


async def triage_node(state: MedBotState) -> MedBotState:
    """Classify triage severity level."""
    logger.info(f"[{state['run_id']}] Triage classification")
    state["pipeline_stage"] = "triage"

    # Fast-path: if emergency already detected, skip expensive call
    if state.get("is_emergency"):
        state["triage_level"] = "EMERGENCY"
        state["risk_assessment"] = {
            "risk_level": "critical",
            "requires_immediate_attention": True,
            "emergency_indicators": ["Emergency symptoms detected in input"],
        }
        return state

    result = await _call_service(
        config.triage_agent_url,
        "/api/v1/triage/classify",
        {
            "symptoms": state.get("extracted_symptoms", []),
            "medical_reasoning": state.get("medical_reasoning", ""),
            "patient_context": state.get("patient_context", {}),
            "query": state["user_query"],
        },
    )

    if result:
        state["triage_level"] = result.get("triage_level", "ROUTINE")
        state["risk_assessment"] = result.get("risk_assessment")
        if result.get("triage_level") == "EMERGENCY":
            state["is_emergency"] = True
    else:
        state["triage_level"] = "ROUTINE"

    logger.info(f"[{state['run_id']}] Triage: {state['triage_level']}")
    return state


async def doctor_recommendation_node(state: MedBotState) -> MedBotState:
    """Recommend appropriate medical specialist."""
    logger.info(f"[{state['run_id']}] Doctor recommendation")
    state["pipeline_stage"] = "doctor_recommendation"

    result = await _call_service(
        config.doctor_recommendation_url,
        "/api/v1/doctors/recommend",
        {
            "symptoms": state.get("extracted_symptoms", []),
            "triage_level": state.get("triage_level", "ROUTINE"),
            "patient_context": state.get("patient_context", {}),
            "medical_reasoning": state.get("medical_reasoning", ""),
        },
    )

    if result:
        state["doctor_recommendation"] = result
    else:
        state["doctor_recommendation"] = {
            "specialty": "General Practice",
            "urgency": state.get("triage_level", "ROUTINE"),
            "reasoning": "Please consult a general practitioner for initial evaluation.",
            "telehealth_appropriate": True,
            "emergency_services": state.get("is_emergency", False),
        }

    return state
