"""Dataset Labeling Model Service - auto-labels medical dataset entries."""
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8050"
    request_timeout: int = 60
    class Config:
        env_prefix = "DATASET_LABEL_"

settings = Settings()

MEDICAL_CATEGORIES = [
    "cardiology", "pulmonology", "neurology", "gastroenterology", "endocrinology",
    "infectious_disease", "oncology", "psychiatry", "pediatrics", "geriatrics",
    "emergency_medicine", "orthopedics", "dermatology", "ophthalmology", "general",
]

SEVERITY_MAP = {
    "emergency": ["cardiac arrest", "stroke", "seizure", "anaphylaxis", "trauma"],
    "urgent": ["chest pain", "high fever", "severe pain", "bleeding", "infection"],
    "routine": ["follow-up", "checkup", "prescription", "chronic", "mild"],
}

def _keyword_categorize(text: str) -> str:
    text_lower = text.lower()
    keyword_map = {
        "cardiology": ["heart", "cardiac", "chest pain", "hypertension", "arrhythmia", "ecg"],
        "pulmonology": ["lung", "breathing", "asthma", "copd", "respiratory", "pneumonia"],
        "neurology": ["brain", "stroke", "seizure", "headache", "migraine", "nerve"],
        "gastroenterology": ["stomach", "abdomen", "bowel", "liver", "colon", "diarrhea"],
        "endocrinology": ["diabetes", "thyroid", "insulin", "glucose", "hormone"],
        "psychiatry": ["anxiety", "depression", "mental", "psychiatric", "mood"],
        "pediatrics": ["child", "infant", "pediatric", "baby", "toddler"],
        "emergency_medicine": ["emergency", "urgent", "critical", "trauma", "acute"],
    }
    for category, keywords in keyword_map.items():
        if any(k in text_lower for k in keywords):
            return category
    return "general"

def _keyword_severity(text: str) -> str:
    text_lower = text.lower()
    for severity, keywords in SEVERITY_MAP.items():
        if any(k in text_lower for k in keywords):
            return severity
    return "routine"

class DatasetLabelingService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        logger.info("DatasetLabelingService started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def label_batch(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        labeled = []
        for example in examples:
            text = f"{example.get('question', '')} {example.get('answer', '')}"
            category = _keyword_categorize(text)
            severity = _keyword_severity(text)
            labeled.append({
                **example,
                "category": category,
                "severity": severity,
                "confidence": 0.75,
                "label_method": "keyword_rules",
            })
        return {
            "labeled_examples": labeled,
            "total": len(labeled),
            "categories": list({e["category"] for e in labeled}),
        }

    def validate_labeled(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid = []
        invalid = []
        for ex in examples:
            issues = []
            if not ex.get("question"):
                issues.append("missing_question")
            if not ex.get("answer"):
                issues.append("missing_answer")
            if ex.get("category") not in MEDICAL_CATEGORIES:
                issues.append("invalid_category")
            if issues:
                invalid.append({"example": ex, "issues": issues})
            else:
                valid.append(ex)
        return {
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "valid_examples": valid,
            "invalid_examples": invalid,
            "validation_passed": len(invalid) == 0,
        }
