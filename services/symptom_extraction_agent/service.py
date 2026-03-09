"""Symptom Extraction Agent - extracts and structures symptoms from natural language."""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SYMPTOM_PATTERNS = {
    "pain": r"\b(?:pain|ache|hurt|sore|tender|discomfort)\b",
    "fever": r"\b(?:fever|temperature|hot|chills|sweating)\b",
    "breathing": r"\b(?:breath|breathe|respiratory|cough|wheeze|chest tight)\b",
    "nausea": r"\b(?:nausea|nauseous|vomit|sick|queasy)\b",
    "fatigue": r"\b(?:tired|fatigue|exhausted|weak|lethargic|energy)\b",
    "headache": r"\b(?:headache|head pain|migraine|head ache)\b",
    "dizziness": r"\b(?:dizzy|dizziness|vertigo|lightheaded|faint)\b",
    "swelling": r"\b(?:swollen|swelling|edema|bloated|puffiness)\b",
}

BODY_PARTS = ["chest", "head", "stomach", "abdomen", "back", "leg", "arm", "neck", "throat", "ear", "eye"]
DURATION_PATTERN = re.compile(r"(?:for\s+)?(\d+\s+(?:day|week|month|hour)s?)", re.IGNORECASE)
SEVERITY_WORDS = {"mild": 1, "moderate": 2, "severe": 3, "extreme": 4, "unbearable": 5}

class SymptomExtractionAgent:
    def __init__(self):
        self._patterns = {k: re.compile(v, re.IGNORECASE) for k, v in SYMPTOM_PATTERNS.items()}

    async def startup(self):
        logger.info("Symptom Extraction Agent ready.")

    async def shutdown(self):
        pass

    async def extract(self, text: str) -> dict:
        symptoms = [name for name, pattern in self._patterns.items() if pattern.search(text)]
        body_parts = [bp for bp in BODY_PARTS if bp in text.lower()]
        duration_match = DURATION_PATTERN.search(text)
        duration = duration_match.group(0) if duration_match else None
        severity_score = max((SEVERITY_WORDS[w] for w in SEVERITY_WORDS if w in text.lower()), default=None)
        return {
            "raw_text": text,
            "extracted_symptoms": symptoms,
            "affected_body_parts": body_parts,
            "duration": duration,
            "severity_score": severity_score,
            "symptom_count": len(symptoms),
        }

    async def structure(self, symptoms: List[str], patient_id: Optional[str] = None) -> dict:
        structured = []
        for symptom in symptoms:
            result = await self.extract(symptom)
            structured.append({
                "symptom_text": symptom,
                "category": result["extracted_symptoms"],
                "body_parts": result["affected_body_parts"],
                "severity": result["severity_score"],
            })
        return {
            "patient_id": patient_id,
            "structured_symptoms": structured,
            "total": len(structured),
            "unique_categories": list(set(cat for s in structured for cat in s["category"])),
        }
