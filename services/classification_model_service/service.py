"""
Classification Model Service - Triage classification and severity scoring.
Uses keyword rules for fast initial classification, then phi3:mini for nuanced reasoning.
"""
import re
import httpx
from typing import List, Optional, Dict, Tuple
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8050"
    request_timeout: int = 60

    class Config:
        env_prefix = "CLASSIFICATION_"


settings = Settings()

# Triage levels in descending urgency
TRIAGE_LEVELS = ["EMERGENCY", "URGENT", "SEMI_URGENT", "ROUTINE", "SELF_CARE"]

# Keyword rule sets for fast pre-classification
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "cardiac arrest", "not breathing", "stopped breathing",
    "unconscious", "unresponsive", "severe bleeding", "heavy bleeding", "stroke",
    "facial drooping", "arm weakness", "speech difficulty", "sudden severe headache",
    "worst headache", "thunderclap headache", "anaphylaxis", "anaphylactic",
    "severe allergic reaction", "throat closing", "can't breathe", "cannot breathe",
    "difficulty breathing", "shortness of breath", "suicide", "overdose",
    "seizure", "convulsion", "choking", "severe burns", "major trauma",
    "head injury", "neck injury", "spinal injury", "loss of consciousness",
    "diabetic coma", "hypoglycemia severe",
]

URGENT_KEYWORDS = [
    "high fever", "fever above 39", "fever above 103", "severe pain",
    "broken bone", "fracture", "dislocation", "deep cut", "laceration",
    "vomiting blood", "blood in stool", "rectal bleeding", "coughing blood",
    "sudden vision loss", "sudden hearing loss", "severe abdominal pain",
    "appendicitis", "kidney stone", "urinary retention", "priapism",
    "psychiatric emergency", "self harm", "acute psychosis",
    "severe infection", "sepsis", "cellulitis spreading",
    "asthma attack moderate", "oxygen", "confusion sudden",
]

SEMI_URGENT_KEYWORDS = [
    "moderate pain", "infection", "UTI", "urinary tract infection",
    "ear infection", "ear pain", "sore throat severe", "strep throat",
    "pink eye", "conjunctivitis", "skin rash", "allergic reaction mild",
    "sprain", "minor fracture", "dental pain", "tooth pain",
    "migraine", "persistent headache", "vomiting", "diarrhea",
    "dehydration", "minor burns", "wound infection",
]

ROUTINE_KEYWORDS = [
    "follow up", "follow-up", "prescription refill", "chronic condition",
    "checkup", "check-up", "annual physical", "vaccination", "immunization",
    "routine screening", "blood pressure check", "diabetes management",
    "cholesterol", "mild symptoms", "persistent cough", "minor rash",
    "fatigue", "tiredness", "insomnia", "anxiety mild", "depression",
]

SELF_CARE_KEYWORDS = [
    "cold", "runny nose", "sneezing", "common cold", "minor sore throat",
    "mild headache", "minor ache", "minor cut", "scrape", "bruise",
    "muscle soreness", "minor sprain", "mild indigestion", "heartburn mild",
    "mild diarrhea", "constipation", "minor sunburn",
]


def keyword_classify(text: str) -> Tuple[Optional[str], float]:
    """
    Apply keyword rules to quickly classify triage level.
    Returns (level, confidence) or (None, 0.0) if no match.
    """
    text_lower = text.lower()

    rule_sets = [
        (EMERGENCY_KEYWORDS, "EMERGENCY", 0.85),
        (URGENT_KEYWORDS, "URGENT", 0.75),
        (SEMI_URGENT_KEYWORDS, "SEMI_URGENT", 0.70),
        (ROUTINE_KEYWORDS, "ROUTINE", 0.65),
        (SELF_CARE_KEYWORDS, "SELF_CARE", 0.65),
    ]

    for keywords, level, base_confidence in rule_sets:
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            # Boost confidence slightly for multiple matches
            confidence = min(0.95, base_confidence + matches * 0.02)
            return level, confidence

    return None, 0.0


async def classify_with_llm(symptoms: str, context: str = "") -> dict:
    """Use phi3:mini to classify triage level with reasoning."""
    prompt = f"""You are a medical triage AI. Classify the following patient presentation into exactly one triage level.

TRIAGE LEVELS (choose exactly one):
- EMERGENCY: Immediate life-threatening, needs emergency services NOW
- URGENT: Serious condition, needs care within 2 hours
- SEMI_URGENT: Needs care today or within 24 hours
- ROUTINE: Non-urgent, can wait for scheduled appointment
- SELF_CARE: Can be managed at home with rest and OTC remedies

Patient symptoms/presentation:
{symptoms}

{f'Additional context: {context}' if context else ''}

Respond in this exact format:
TRIAGE_LEVEL: [level]
CONFIDENCE: [0.0-1.0]
REASONING: [brief clinical reasoning, 2-3 sentences]
RED_FLAGS: [comma-separated list of concerning features, or NONE]"""

    payload = {
        "prompt": prompt,
        "task_type": "classification",
        "temperature": 0.1,
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_router_url}/api/v1/model/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return parse_llm_triage_response(data.get("response", ""))


def parse_llm_triage_response(response_text: str) -> dict:
    """Parse the structured LLM triage response."""
    lines = response_text.strip().split("\n")
    result = {
        "triage_level": "ROUTINE",
        "confidence": 0.5,
        "reasoning": response_text,
        "red_flags": [],
    }

    for line in lines:
        if line.startswith("TRIAGE_LEVEL:"):
            level_str = line.split(":", 1)[1].strip().upper()
            if level_str in TRIAGE_LEVELS:
                result["triage_level"] = level_str
        elif line.startswith("CONFIDENCE:"):
            try:
                conf = float(line.split(":", 1)[1].strip())
                result["confidence"] = max(0.0, min(1.0, conf))
            except ValueError:
                pass
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()
        elif line.startswith("RED_FLAGS:"):
            flags_str = line.split(":", 1)[1].strip()
            if flags_str.upper() != "NONE":
                result["red_flags"] = [f.strip() for f in flags_str.split(",") if f.strip()]

    return result


# Severity score map
SEVERITY_LEVELS = {
    "CRITICAL": (9, 10),
    "SEVERE": (7, 8),
    "MODERATE": (4, 6),
    "MILD": (2, 3),
    "MINIMAL": (0, 1),
}

SEVERITY_KEYWORDS = {
    "CRITICAL": ["excruciating", "unbearable", "worst ever", "10/10", "dying", "cannot move", "paralyzed"],
    "SEVERE": ["severe", "intense", "very bad", "8/10", "9/10", "debilitating", "can't function"],
    "MODERATE": ["moderate", "significant", "5/10", "6/10", "7/10", "affecting daily", "troublesome"],
    "MILD": ["mild", "slight", "minor", "2/10", "3/10", "4/10", "manageable", "occasional"],
    "MINIMAL": ["very mild", "barely", "1/10", "hardly noticeable", "almost gone", "resolving"],
}


def keyword_severity(text: str) -> Tuple[Optional[str], float, int]:
    """
    Classify symptom severity by keyword matching.
    Returns (level, confidence, score).
    """
    text_lower = text.lower()

    for level, keywords in SEVERITY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            score_range = SEVERITY_LEVELS[level]
            score = score_range[1] if matches > 1 else score_range[0]
            return level, min(0.85, 0.65 + matches * 0.05), score

    return None, 0.0, 5


async def classify_severity(symptoms: str, pain_scale: Optional[int] = None) -> dict:
    """Classify symptom severity using keyword rules and LLM."""
    # Quick keyword check
    kw_level, kw_conf, kw_score = keyword_severity(symptoms)

    # If pain scale provided, use it as anchor
    if pain_scale is not None:
        if pain_scale >= 9:
            kw_level, kw_score = "CRITICAL", pain_scale
        elif pain_scale >= 7:
            kw_level, kw_score = "SEVERE", pain_scale
        elif pain_scale >= 4:
            kw_level, kw_score = "MODERATE", pain_scale
        elif pain_scale >= 2:
            kw_level, kw_score = "MILD", pain_scale
        else:
            kw_level, kw_score = "MINIMAL", pain_scale
        kw_conf = 0.80

    if kw_conf >= 0.75:
        return {
            "severity_level": kw_level or "MODERATE",
            "severity_score": kw_score,
            "confidence": kw_conf,
            "method": "keyword_rules",
            "reasoning": f"Classified as {kw_level} based on symptom descriptors.",
        }

    # Fallback to LLM
    prompt = f"""Rate the severity of these symptoms on a clinical scale.

Symptoms: {symptoms}
{f'Patient reported pain scale: {pain_scale}/10' if pain_scale else ''}

Respond in this format:
SEVERITY_LEVEL: [CRITICAL/SEVERE/MODERATE/MILD/MINIMAL]
SEVERITY_SCORE: [0-10]
CONFIDENCE: [0.0-1.0]
REASONING: [brief clinical assessment]"""

    payload = {"prompt": prompt, "task_type": "classification", "temperature": 0.1, "max_tokens": 200}

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_router_url}/api/v1/model/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return parse_severity_response(data.get("response", ""), kw_score)


def parse_severity_response(response_text: str, fallback_score: int = 5) -> dict:
    """Parse structured LLM severity response."""
    lines = response_text.strip().split("\n")
    result = {
        "severity_level": "MODERATE",
        "severity_score": fallback_score,
        "confidence": 0.5,
        "method": "llm_classification",
        "reasoning": response_text,
    }

    for line in lines:
        if line.startswith("SEVERITY_LEVEL:"):
            level = line.split(":", 1)[1].strip().upper()
            if level in SEVERITY_LEVELS:
                result["severity_level"] = level
        elif line.startswith("SEVERITY_SCORE:"):
            try:
                result["severity_score"] = int(float(line.split(":", 1)[1].strip()))
            except ValueError:
                pass
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = max(0.0, min(1.0, float(line.split(":", 1)[1].strip())))
            except ValueError:
                pass
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result


async def triage_classify(
    symptoms: str,
    patient_age: Optional[int] = None,
    patient_context: Optional[str] = None,
) -> dict:
    """
    Full triage classification pipeline:
    1. Fast keyword rules for high-confidence cases
    2. LLM (phi3:mini) for nuanced classification
    """
    # Build context string
    context_parts = []
    if patient_age is not None:
        context_parts.append(f"Patient age: {patient_age}")
        # Age-specific risk adjustments
        if patient_age < 2 or patient_age > 75:
            context_parts.append("NOTE: High-risk age group - err toward higher urgency")
    if patient_context:
        context_parts.append(patient_context)
    context = ". ".join(context_parts)

    # Try keyword classification first
    kw_level, kw_conf = keyword_classify(symptoms)

    if kw_conf >= 0.80:
        # High-confidence keyword match - skip LLM for speed
        return {
            "triage_level": kw_level,
            "confidence": kw_conf,
            "reasoning": f"Classified as {kw_level} based on high-priority symptom keywords.",
            "red_flags": [],
            "method": "keyword_rules",
            "patient_age": patient_age,
        }

    # LLM classification
    llm_result = await classify_with_llm(symptoms, context)

    # If keyword gave a result but lower confidence, blend
    if kw_level and kw_conf > 0.0:
        # If keyword is more urgent than LLM, trust keyword for safety
        kw_idx = TRIAGE_LEVELS.index(kw_level)
        llm_idx = TRIAGE_LEVELS.index(llm_result["triage_level"])
        if kw_idx < llm_idx:  # keyword is more urgent
            llm_result["triage_level"] = kw_level
            llm_result["reasoning"] += f" (Elevated by keyword rules detecting: {kw_level})"

    llm_result["method"] = "llm_classification"
    llm_result["patient_age"] = patient_age
    return llm_result
