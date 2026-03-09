"""WHO Guidelines Service - retrieves WHO clinical guidelines."""
import logging
import httpx
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Sample WHO guidelines database (in production, use actual WHO API or database)
WHO_GUIDELINES: Dict[str, dict] = {
    "diabetes-management": {
        "guideline_id": "diabetes-management",
        "title": "WHO Global Report on Diabetes",
        "category": "chronic_disease",
        "summary": "Guidelines for diabetes prevention, management and care",
        "key_recommendations": [
            "Maintain HbA1c below 7% for most patients",
            "Screen for complications annually",
            "Promote lifestyle modifications including diet and exercise"
        ],
        "url": "https://www.who.int/publications/i/item/9789241565257"
    },
    "hypertension-management": {
        "guideline_id": "hypertension-management",
        "title": "WHO Guideline for the Pharmacological Treatment of Hypertension in Adults",
        "category": "cardiovascular",
        "summary": "Evidence-based recommendations for hypertension treatment",
        "key_recommendations": [
            "Blood pressure target <140/90 mmHg for most adults",
            "First-line agents: thiazides, ACE inhibitors, ARBs, or calcium channel blockers",
            "Lifestyle modifications as first-line intervention"
        ],
        "url": "https://www.who.int/publications/i/item/9789240033986"
    },
    "mental-health-action": {
        "guideline_id": "mental-health-action",
        "title": "WHO Mental Health Action Plan 2013-2030",
        "category": "mental_health",
        "summary": "Global action plan for mental health services and care",
        "key_recommendations": [
            "Integrate mental health into primary care",
            "Promote mental health and prevent mental disorders",
            "Strengthen information systems for mental health"
        ],
        "url": "https://www.who.int/publications/i/item/9789240031029"
    },
}

class WHOGuidelinesService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._guidelines = WHO_GUIDELINES.copy()

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info("WHO Guidelines Service ready with %d guidelines.", len(self._guidelines))

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def search(self, query: str, category: Optional[str] = None) -> dict:
        query_lower = query.lower()
        results = []
        for guideline in self._guidelines.values():
            if category and guideline.get("category") != category:
                continue
            if (query_lower in guideline["title"].lower() or
                query_lower in guideline["summary"].lower() or
                query_lower in guideline["guideline_id"]):
                results.append(guideline)
        return {"query": query, "results": results, "total": len(results), "source": "WHO"}

    async def get_guideline(self, guideline_id: str) -> Optional[dict]:
        return self._guidelines.get(guideline_id)
