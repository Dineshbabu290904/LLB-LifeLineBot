import re
import httpx
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8010"
    llm_model: str = "llama3.2"
    llm_timeout: float = 30.0
    use_llm_augmentation: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# ---------------------------------------------------------------------------
# Severity level definitions
# ---------------------------------------------------------------------------

SEVERITY_LEVELS = {
    "mild": {"range": (0, 25), "label": "mild", "description": "Symptoms are manageable; self-care is appropriate."},
    "moderate": {"range": (26, 50), "label": "moderate", "description": "Symptoms warrant medical evaluation within 24-48 hours."},
    "severe": {"range": (51, 75), "label": "severe", "description": "Symptoms require prompt medical attention, same day or urgent care."},
    "critical": {"range": (76, 100), "label": "critical", "description": "Potentially life-threatening; emergency care required immediately."},
}

# ---------------------------------------------------------------------------
# Symptom scoring tables
# ---------------------------------------------------------------------------

# Base scores for symptoms (0-30 per symptom, cumulative up to 100)
SYMPTOM_BASE_SCORES: Dict[str, int] = {
    # Critical (30 pts each)
    "chest pain": 30,
    "myocardial infarction": 30,
    "cardiac arrest": 30,
    "stroke": 30,
    "hemoptysis": 28,
    "unconscious": 30,
    "loss of consciousness": 30,
    "seizure": 28,
    "anaphylaxis": 30,
    "respiratory failure": 30,
    "sepsis": 30,
    "pulmonary embolism": 30,
    # Severe (20-25 pts each)
    "dyspnea": 22,
    "shortness of breath": 22,
    "severe headache": 25,
    "worst headache": 28,
    "thunderclap headache": 28,
    "sudden weakness": 25,
    "unilateral weakness": 25,
    "facial droop": 25,
    "slurred speech": 25,
    "vomiting blood": 28,
    "rectal bleeding": 22,
    "severe abdominal pain": 22,
    "high fever": 20,
    "altered consciousness": 28,
    "confusion": 20,
    "syncope": 22,
    "fainting": 20,
    "palpitations": 18,
    # Moderate (10-18 pts each)
    "fever": 12,
    "cough": 8,
    "abdominal pain": 14,
    "back pain": 12,
    "joint pain": 10,
    "rash": 10,
    "dizziness": 14,
    "nausea": 8,
    "vomiting": 12,
    "diarrhea": 10,
    "fatigue": 8,
    "edema": 12,
    "dysuria": 10,
    "headache": 10,
    "chest tightness": 20,
    "sore throat": 6,
    # Mild (1-8 pts each)
    "runny nose": 4,
    "sneezing": 3,
    "mild cough": 5,
    "itching": 5,
    "mild headache": 6,
    "muscle ache": 6,
    "pruritus": 5,
    "rhinorrhea": 4,
    "myalgia": 7,
}

# Modifiers that multiply the base score
ONSET_MODIFIERS: Dict[str, float] = {
    "sudden": 1.5,
    "abrupt": 1.5,
    "acute": 1.4,
    "rapidly": 1.4,
    "quickly": 1.3,
    "gradual": 0.8,
    "slowly": 0.7,
    "chronic": 0.6,
    "intermittent": 0.75,
}

DURATION_MODIFIERS: Dict[str, Tuple[re.Pattern, float]] = {
    "minutes": (re.compile(r"\b\d+\s*(?:minutes?|mins?)\b", re.I), 1.3),
    "hours_short": (re.compile(r"\b[1-3]\s*hours?\b", re.I), 1.1),
    "hours_long": (re.compile(r"\b(?:[4-9]|[1-9]\d)\s*hours?\b", re.I), 1.0),
    "days": (re.compile(r"\b\d+\s*days?\b", re.I), 0.9),
    "weeks": (re.compile(r"\b\d+\s*weeks?\b", re.I), 0.8),
    "months": (re.compile(r"\b\d+\s*months?\b", re.I), 0.7),
}

SEVERITY_MODIFIER_WORDS: Dict[str, float] = {
    "severe": 1.4,
    "excruciating": 1.5,
    "unbearable": 1.5,
    "worst": 1.5,
    "extreme": 1.4,
    "intense": 1.3,
    "sharp": 1.2,
    "stabbing": 1.2,
    "crushing": 1.3,
    "mild": 0.6,
    "slight": 0.5,
    "minor": 0.5,
    "little": 0.6,
    "dull": 0.7,
}

HIGH_RISK_HISTORY: List[str] = [
    "diabetes", "diabetic", "heart disease", "heart failure", "cardiac",
    "hypertension", "blood pressure", "cancer", "copd", "asthma",
    "immunocompromised", "hiv", "aids", "kidney disease", "liver disease",
    "anticoagulant", "warfarin", "blood thinner", "pregnant", "pregnancy",
    "elderly", "immunosuppressed", "transplant",
]


class SeverityResult(BaseModel):
    severity_level: str
    score: int
    factors: List[str]
    description: str
    recommendation: str


def _score_symptoms(symptoms: List[str], text_context: str = "") -> Tuple[int, List[str]]:
    """Score symptoms using the base table and modifiers."""
    factors: List[str] = []
    raw_score: float = 0.0
    combined = " ".join(symptoms).lower() + " " + text_context.lower()

    # Score each symptom
    matched_symptoms = set()
    for symptom in symptoms:
        s_lower = symptom.lower().strip()
        best_match = None
        best_score = 0
        for key, score in SYMPTOM_BASE_SCORES.items():
            if key in s_lower or s_lower in key:
                if score > best_score:
                    best_score = score
                    best_match = key
        if best_match and best_match not in matched_symptoms:
            matched_symptoms.add(best_match)
            raw_score += best_score
            factors.append(f"Symptom '{best_match}' (base score: {best_score})")

    # Multiple symptoms increase severity
    if len(matched_symptoms) >= 3:
        bonus = min((len(matched_symptoms) - 2) * 5, 20)
        raw_score += bonus
        factors.append(f"Multiple symptoms ({len(matched_symptoms)}) adds {bonus} points")

    # Onset modifier
    onset_mod = 1.0
    for word, mod in ONSET_MODIFIERS.items():
        if re.search(rf"\b{re.escape(word)}\b", combined, re.I):
            onset_mod = max(onset_mod, mod)
            factors.append(f"Onset modifier '{word}' (x{mod})")
            break

    # Duration modifier
    dur_mod = 1.0
    for key, (pattern, mod) in DURATION_MODIFIERS.items():
        if pattern.search(combined):
            dur_mod = mod
            factors.append(f"Duration modifier '{key}' (x{mod})")
            break

    # Severity word modifier
    sev_mod = 1.0
    for word, mod in SEVERITY_MODIFIER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", combined, re.I):
            sev_mod = max(sev_mod, mod) if mod > 1 else min(sev_mod, mod)
            factors.append(f"Severity qualifier '{word}' (x{mod})")

    final_score = raw_score * onset_mod * dur_mod * sev_mod
    return min(int(final_score), 100), factors


def _check_patient_history(patient_history: Optional[str]) -> Tuple[int, List[str]]:
    """Add score for high-risk patient history."""
    if not patient_history:
        return 0, []
    bonus = 0
    factors = []
    ph_lower = patient_history.lower()
    for risk_item in HIGH_RISK_HISTORY:
        if risk_item in ph_lower:
            bonus += 5
            factors.append(f"High-risk history: {risk_item} (+5)")
    return min(bonus, 20), factors


def _score_to_level(score: int) -> Dict:
    """Convert numeric score to severity level."""
    for level, info in SEVERITY_LEVELS.items():
        lo, hi = info["range"]
        if lo <= score <= hi:
            return info
    return SEVERITY_LEVELS["critical"]


def _get_recommendation(level: str) -> str:
    recs = {
        "mild": "Rest, hydration, and OTC remedies are appropriate. Monitor for worsening. See a doctor if symptoms persist beyond 3-5 days.",
        "moderate": "Schedule a medical appointment within 24-48 hours. Avoid strenuous activity. Monitor symptoms closely.",
        "severe": "Seek urgent medical care today. Visit an urgent care center or call your doctor immediately.",
        "critical": "Call emergency services (911) immediately or go to the nearest emergency room. Do not drive yourself.",
    }
    return recs.get(level, "Seek medical attention.")


async def classify_severity_with_llm(
    symptoms: List[str],
    base_score: int,
    patient_history: Optional[str],
    context_factors: List[str],
) -> Optional[Dict]:
    """Use LLM to validate and potentially adjust severity classification."""
    symptoms_str = ", ".join(symptoms)
    history_str = patient_history or "none"

    prompt = (
        "You are a medical triage expert. Evaluate symptom severity.\n"
        f"Symptoms: {symptoms_str}\n"
        f"Patient history: {history_str}\n"
        f"Rule-based score: {base_score}/100\n"
        "Respond in format:\n"
        "ADJUSTED_SCORE: <0-100>\n"
        "REASON: <brief reason>\n"
        "Only adjust if the rule-based score is clearly wrong. Otherwise confirm it."
    )

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.ollama_router_url}/api/generate",
                json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")

        score_match = re.search(r"ADJUSTED_SCORE:\s*(\d+)", raw, re.I)
        reason_match = re.search(r"REASON:\s*(.+)", raw, re.I)

        if score_match:
            llm_score = min(int(score_match.group(1)), 100)
            reason = reason_match.group(1).strip() if reason_match else "LLM adjustment"
            return {"score": llm_score, "reason": reason}
    except Exception:
        pass
    return None


async def classify_severity(
    symptoms: List[str],
    patient_history: Optional[str] = None,
    duration: Optional[str] = None,
    onset: Optional[str] = None,
    use_llm: bool = True,
) -> SeverityResult:
    """Full severity classification pipeline."""
    context = " ".join(filter(None, [duration, onset]))
    base_score, sym_factors = _score_symptoms(symptoms, context)
    history_bonus, hist_factors = _check_patient_history(patient_history)

    total_score = min(base_score + history_bonus, 100)
    all_factors = sym_factors + hist_factors

    if use_llm and settings.use_llm_augmentation and total_score > 0:
        llm_result = await classify_severity_with_llm(symptoms, total_score, patient_history, all_factors)
        if llm_result:
            # Blend: 70% rule-based, 30% LLM
            blended = int(total_score * 0.7 + llm_result["score"] * 0.3)
            if abs(blended - total_score) > 5:
                all_factors.append(f"LLM adjustment: {llm_result['reason']}")
            total_score = blended

    level_info = _score_to_level(total_score)
    level = level_info["label"]

    return SeverityResult(
        severity_level=level,
        score=total_score,
        factors=all_factors,
        description=level_info["description"],
        recommendation=_get_recommendation(level),
    )
