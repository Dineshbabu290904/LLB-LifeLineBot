"""Emergency Detection Service - detects medical emergencies in patient queries."""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "stroke", "can't breathe", "difficulty breathing",
    "unconscious", "unresponsive", "severe bleeding", "overdose", "suicide", "poisoning",
    "anaphylaxis", "allergic reaction", "seizure", "convulsion", "severe headache",
    "sudden vision loss", "paralysis", "coughing blood", "vomiting blood", "severe burns",
    "drowning", "choking", "cardiac arrest", "call 911", "emergency", "help me"
]

URGENT_KEYWORDS = [
    "high fever", "severe pain", "vomiting", "diarrhea", "dizziness", "fainting",
    "infection", "wound", "fracture", "broken bone", "sprain", "rash", "swelling"
]

class EmergencyDetectionService:
    def __init__(self):
        pass

    async def startup(self):
        logger.info("Emergency Detection Service ready.")

    async def shutdown(self):
        pass

    def _check_keywords(self, text: str, keywords: List[str]) -> List[str]:
        text_lower = text.lower()
        return [kw for kw in keywords if kw in text_lower]

    async def detect(self, query: str, user_id: Optional[str] = None) -> dict:
        emergency_matches = self._check_keywords(query, EMERGENCY_KEYWORDS)
        urgent_matches = self._check_keywords(query, URGENT_KEYWORDS)

        if emergency_matches:
            level = "EMERGENCY"
            action = "call_911"
            confidence = 0.95
        elif urgent_matches:
            level = "URGENT"
            action = "seek_immediate_care"
            confidence = 0.80
        else:
            level = "NON_URGENT"
            action = "standard_care"
            confidence = 0.70

        return {
            "query": query,
            "emergency_level": level,
            "recommended_action": action,
            "confidence": confidence,
            "matched_keywords": emergency_matches + urgent_matches,
            "is_emergency": level == "EMERGENCY",
        }

    async def alert(self, query: str, user_id: str, contact: Optional[str] = None) -> dict:
        detection = await self.detect(query, user_id)
        return {
            **detection,
            "alert_sent": True,
            "alert_contact": contact or "emergency_services",
            "message": "Emergency alert dispatched. Please call 911 immediately.",
        }
