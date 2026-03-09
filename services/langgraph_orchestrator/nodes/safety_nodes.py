"""Safety guardrail nodes — input and output checkpoints."""
import httpx
import re
import logging
from state import MedBotState
from config import get_config

logger = logging.getLogger("safety_nodes")
config = get_config()

# Emergency patterns checked synchronously (no service call needed)
EMERGENCY_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"chest pain.*(shortness of breath|sweating|arm pain|jaw pain)",
        r"(cannot breathe|can't breathe|not breathing)",
        r"(heart attack|cardiac arrest)",
        r"(unconscious|unresponsive)",
        r"stroke",
        r"(suicidal|suicide|want to die|kill myself)",
        r"overdose",
        r"severe (bleeding|allergic reaction)",
        r"anaphylaxis",
    ]
]

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"ignore (previous|all|above) (instructions?|prompt)",
        r"forget (everything|all) (you|previously)",
        r"you are now",
        r"jailbreak",
        r"DAN mode",
        r"system prompt",
    ]
]


async def safety_input_node(state: MedBotState) -> MedBotState:
    """Check input safety before processing."""
    logger.info(f"[{state['run_id']}] Safety input check")
    state["pipeline_stage"] = "safety_input"

    query = state.get("user_query", "")
    violations = []

    # Check for prompt injection
    for pattern in INJECTION_PATTERNS:
        if pattern.search(query):
            violations.append(f"Prompt injection detected")
            break

    # Check for emergency
    is_emergency = any(p.search(query) for p in EMERGENCY_PATTERNS)
    state["is_emergency"] = is_emergency

    # Truncate excessively long queries
    if len(query) > 2000:
        state["user_query"] = query[:2000]
        violations.append("Query truncated to 2000 characters")

    state["safety_violations"] = violations
    state["input_safety_cleared"] = len([v for v in violations if "injection" in v.lower()]) == 0

    if is_emergency:
        logger.warning(f"[{state['run_id']}] EMERGENCY detected in query")

    return state


async def safety_output_node(state: MedBotState) -> MedBotState:
    """Check output safety before returning response."""
    logger.info(f"[{state['run_id']}] Safety output check")
    state["pipeline_stage"] = "safety_output"

    response = state.get("final_response", "")
    violations = list(state.get("safety_violations", []))

    # Check disclaimer presence
    has_disclaimer = any(
        phrase in response.lower()
        for phrase in ["disclaimer", "consult", "healthcare professional", "medical advice"]
    )
    if not has_disclaimer:
        violations.append("Missing medical disclaimer")

    # Inject disclaimer
    disclaimer = (
        "\n\n⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
        "and does not constitute medical advice. Always consult a qualified healthcare "
        "professional for medical decisions. In case of emergency, call emergency services immediately."
    )
    if not has_disclaimer:
        response += disclaimer

    # Emergency escalation
    if state.get("is_emergency") or state.get("triage_level") == "EMERGENCY":
        emergency_note = (
            "\n\n🚨 EMERGENCY: Based on symptoms described, seek immediate emergency care. "
            "Call 911 or go to the nearest emergency room immediately."
        )
        if "emergency" not in response.lower():
            response += emergency_note

    # Block if hallucination is too high
    if state.get("hallucination_score", 0) > 0.7:
        response = (
            "I was unable to provide a reliable medical assessment based on verified sources. "
            "Please consult a qualified healthcare professional directly." + disclaimer
        )
        violations.append("Response blocked: hallucination score too high")

    state["final_response"] = response
    state["safety_violations"] = violations
    state["output_safety_cleared"] = True

    return state
