"""Doctor Recommendation Agent - recommends doctors based on symptoms and location."""
import logging
import uuid
from typing import Any, Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    doctor_mapping_url: str = "http://doctor_mapping_service:8080"
    request_timeout: int = 30
    class Config:
        env_prefix = "DOCTOR_REC_"

settings = Settings()

MOCK_DOCTORS = [
    {"id": "dr001", "name": "Dr. Sarah Chen", "specialty": "cardiology", "rating": 4.8, "years_exp": 15, "location": "New York", "availability": "available"},
    {"id": "dr002", "name": "Dr. James Wilson", "specialty": "neurology", "rating": 4.7, "years_exp": 20, "location": "Boston", "availability": "available"},
    {"id": "dr003", "name": "Dr. Amira Patel", "specialty": "pulmonology", "rating": 4.9, "years_exp": 12, "location": "Chicago", "availability": "next_week"},
    {"id": "dr004", "name": "Dr. Carlos Rivera", "specialty": "gastroenterology", "rating": 4.6, "years_exp": 18, "location": "Miami", "availability": "available"},
    {"id": "dr005", "name": "Dr. Emily Thompson", "specialty": "endocrinology", "rating": 4.8, "years_exp": 10, "location": "Seattle", "availability": "available"},
    {"id": "dr006", "name": "Dr. Michael Okonkwo", "specialty": "orthopedics", "rating": 4.7, "years_exp": 22, "location": "Houston", "availability": "available"},
    {"id": "dr007", "name": "Dr. Lisa Park", "specialty": "psychiatry", "rating": 4.9, "years_exp": 14, "location": "San Francisco", "availability": "available"},
    {"id": "dr008", "name": "Dr. Robert Kumar", "specialty": "infectious_disease", "rating": 4.8, "years_exp": 16, "location": "Atlanta", "availability": "next_week"},
    {"id": "dr009", "name": "Dr. Anna Kowalski", "specialty": "oncology", "rating": 4.9, "years_exp": 25, "location": "Denver", "availability": "available"},
    {"id": "dr010", "name": "Dr. Hassan Al-Rashid", "specialty": "general_practice", "rating": 4.6, "years_exp": 8, "location": "Phoenix", "availability": "available"},
]


class DoctorRecommendationAgent:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)
        logger.info("DoctorRecommendationAgent started")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Not started")
        return self._client

    async def _get_specialty(self, symptoms: List[str]) -> str:
        try:
            resp = await self.client.post(
                f"{settings.doctor_mapping_url}/api/v1/doctor-mapping/map",
                json={"symptoms": symptoms},
            )
            resp.raise_for_status()
            return resp.json().get("primary_specialty", "general_practice")
        except Exception:
            return "general_practice"

    async def recommend(
        self,
        symptoms: List[str],
        location: Optional[str] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        specialty = await self._get_specialty(symptoms)
        candidates = [d for d in MOCK_DOCTORS if d["specialty"] == specialty]
        if not candidates:
            candidates = [d for d in MOCK_DOCTORS if d["specialty"] == "general_practice"]

        if location:
            loc_lower = location.lower()
            local = [d for d in candidates if loc_lower in d["location"].lower()]
            if local:
                candidates = local

        ranked = sorted(candidates, key=lambda d: (d["rating"], d["years_exp"]), reverse=True)
        return {
            "recommended_specialty": specialty,
            "doctors": ranked[:max_results],
            "total_found": len(candidates),
            "symptoms": symptoms,
            "location": location,
        }

    async def rank_doctors(self, doctors: List[Dict[str, Any]], criteria: Dict[str, Any]) -> Dict[str, Any]:
        weight_rating = criteria.get("rating_weight", 0.5)
        weight_exp = criteria.get("experience_weight", 0.3)
        weight_avail = criteria.get("availability_weight", 0.2)
        avail_scores = {"available": 1.0, "next_week": 0.5, "unavailable": 0.0}

        def score(d: Dict[str, Any]) -> float:
            r = d.get("rating", 0) / 5.0
            e = min(d.get("years_exp", 0) / 30.0, 1.0)
            a = avail_scores.get(d.get("availability", "unavailable"), 0.0)
            return weight_rating * r + weight_exp * e + weight_avail * a

        ranked = sorted(doctors, key=score, reverse=True)
        for i, d in enumerate(ranked):
            d["rank"] = i + 1
            d["score"] = round(score(d), 3)
        return {"ranked_doctors": ranked, "criteria_used": criteria}
