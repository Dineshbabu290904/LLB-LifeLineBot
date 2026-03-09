"""Triage Agent - triages patient queries into severity levels and routes."""
import logging
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)
EMERGENCY_DETECTION_URL = os.getenv("EMERGENCY_DETECTION_URL", "http://emergency_detection_service:8072")

TRIAGE_LEVELS = {
    "EMERGENCY": {"level": 1, "response_time": "immediate", "route_to": "emergency_services"},
    "URGENT": {"level": 2, "response_time": "within_hours", "route_to": "urgent_care"},
    "SEMI_URGENT": {"level": 3, "response_time": "within_24h", "route_to": "primary_care"},
    "NON_URGENT": {"level": 4, "response_time": "scheduled", "route_to": "standard_medbot"},
    "ADVISORY": {"level": 5, "response_time": "self_care", "route_to": "health_information"},
}

class TriageAgent:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info("Triage Agent ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def assess(self, query: str, user_id: Optional[str] = None) -> dict:
        try:
            resp = await self._client.post(
                f"{EMERGENCY_DETECTION_URL}/api/v1/emergency-detection/detect",
                json={"query": query, "user_id": user_id}
            )
            resp.raise_for_status()
            detection = resp.json()
            emergency_level = detection.get("emergency_level", "NON_URGENT")
        except Exception as e:
            logger.warning("Emergency detection failed: %s", e)
            emergency_level = "NON_URGENT"
            detection = {}

        # Map emergency level to triage level
        if emergency_level == "EMERGENCY":
            triage_level = "EMERGENCY"
        elif emergency_level == "URGENT":
            triage_level = "URGENT"
        else:
            # Simple keyword-based triage for non-emergency
            query_lower = query.lower()
            if any(w in query_lower for w in ["surgery", "hospitalize", "specialist", "prescription"]):
                triage_level = "SEMI_URGENT"
            elif any(w in query_lower for w in ["symptom", "sick", "pain", "medication"]):
                triage_level = "NON_URGENT"
            else:
                triage_level = "ADVISORY"

        triage_info = TRIAGE_LEVELS[triage_level]
        return {
            "query": query,
            "triage_level": triage_level,
            "priority": triage_info["level"],
            "recommended_response_time": triage_info["response_time"],
            "route_to": triage_info["route_to"],
            "emergency_detection": detection,
        }

    async def route(self, query: str, user_id: Optional[str] = None) -> dict:
        assessment = await self.assess(query, user_id)
        return {
            **assessment,
            "routing_decision": assessment["route_to"],
            "routing_metadata": {"user_id": user_id, "query_length": len(query)},
        }
