"""Risk Detection Service - detects health risks in patient conversations."""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RISK_FACTORS = {
    "cardiovascular": ["chest pain", "shortness of breath", "heart palpitations", "high blood pressure", "high cholesterol"],
    "diabetes": ["high blood sugar", "excessive thirst", "frequent urination", "blurred vision", "fatigue"],
    "mental_health": ["depression", "anxiety", "suicidal thoughts", "self-harm", "hopelessness"],
    "respiratory": ["chronic cough", "wheezing", "difficulty breathing", "chest tightness"],
    "oncological": ["unexplained weight loss", "persistent fatigue", "unusual lumps", "blood in stool"],
}

class RiskDetectionService:
    def __init__(self):
        pass

    async def startup(self):
        logger.info("Risk Detection Service ready.")

    async def shutdown(self):
        pass

    def _detect_risks(self, text: str) -> Dict[str, List[str]]:
        text_lower = text.lower()
        detected = {}
        for category, factors in RISK_FACTORS.items():
            matched = [f for f in factors if f in text_lower]
            if matched:
                detected[category] = matched
        return detected

    async def detect(self, text: str, user_id: Optional[str] = None) -> dict:
        risks = self._detect_risks(text)
        risk_level = "high" if len(risks) > 2 else ("medium" if risks else "low")
        return {
            "text": text,
            "detected_risks": risks,
            "risk_categories": list(risks.keys()),
            "risk_level": risk_level,
            "requires_attention": bool(risks),
            "user_id": user_id,
        }

    async def assess(self, text: str, age: Optional[int] = None, medical_history: Optional[List[str]] = None) -> dict:
        risks = self._detect_risks(text)
        score = len(risks) * 0.2
        if age and age > 60:
            score += 0.1
        if medical_history:
            score += min(0.3, len(medical_history) * 0.05)
        score = min(1.0, score)
        return {
            "risk_score": round(score, 2),
            "risk_level": "high" if score > 0.6 else ("medium" if score > 0.3 else "low"),
            "detected_risks": risks,
            "age_factor": age,
            "history_factor": medical_history,
            "recommendations": ["Consult a healthcare professional"] if score > 0.3 else [],
        }
