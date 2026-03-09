"""
Response Scoring Service

Orchestrates calls to four sub-services and computes a composite quality score:
  composite = triage_accuracy * 0.25
            + medical_consistency * 0.20
            + (1 - hallucination_rate) * 0.20
            + safety_score * 0.20
            + grounding_score * 0.15

A composite_score < RETRAIN_THRESHOLD triggers requires_retraining=True.
"""
import asyncio
import logging
import os
from typing import List, Optional
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("response_scoring_service")

# Service URLs — overrideable via environment variables
TRIAGE_URL = os.getenv("TRIAGE_ACCURACY_URL", "http://triage_accuracy_service:8101")
CONSISTENCY_URL = os.getenv("MEDICAL_CONSISTENCY_URL", "http://medical_consistency_service:8102")
SAFETY_URL = os.getenv("SAFETY_VALIDATION_URL", "http://safety_validation_service:8103")
HALLUCINATION_URL = os.getenv("HALLUCINATION_DETECTION_URL", "http://hallucination_detection_agent:8104")

# Scoring weights
W_TRIAGE = 0.25
W_CONSISTENCY = 0.20
W_HALLUCINATION = 0.20   # weighted as (1 - hallucination_rate)
W_SAFETY = 0.20
W_GROUNDING = 0.15

RETRAIN_THRESHOLD = 0.60  # composite score below this triggers retraining flag
TIMEOUT = 10.0            # seconds per sub-service call


async def _call_triage(client: httpx.AsyncClient, symptoms: str, triage_level: str, conv_id: str) -> float:
    """Return accuracy_score (0-1) from triage_accuracy_service."""
    try:
        r = await client.post(
            f"{TRIAGE_URL}/api/v1/triage/validate",
            json={"symptoms": symptoms, "actual_level": triage_level, "conversation_id": conv_id},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return float(r.json().get("accuracy_score", 0.5))
    except Exception as exc:
        logger.warning("Triage service error: %s — defaulting to 0.5", exc)
        return 0.5


async def _call_consistency(client: httpx.AsyncClient, response: str, sources: List[str], conv_id: str) -> float:
    """Return consistency_score (0-1) from medical_consistency_service."""
    try:
        r = await client.post(
            f"{CONSISTENCY_URL}/api/v1/consistency/check",
            json={"response": response, "retrieved_sources": sources, "conversation_id": conv_id},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return float(r.json().get("consistency_score", 0.5))
    except Exception as exc:
        logger.warning("Consistency service error: %s — defaulting to 0.5", exc)
        return 0.5


async def _call_safety(client: httpx.AsyncClient, response: str, query: str, triage_level: str, conv_id: str) -> float:
    """Return overall_score (0-1) from safety_validation_service."""
    try:
        r = await client.post(
            f"{SAFETY_URL}/api/v1/safety/validate",
            json={"response": response, "query": query, "triage_level": triage_level, "conversation_id": conv_id},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return float(r.json().get("overall_score", 0.5))
    except Exception as exc:
        logger.warning("Safety service error: %s — defaulting to 0.5", exc)
        return 0.5


async def _call_hallucination(client: httpx.AsyncClient, response: str, sources: List[str], conv_id: str) -> float:
    """Return hallucination_rate (0-1) from hallucination_detection_agent."""
    try:
        r = await client.post(
            f"{HALLUCINATION_URL}/api/v1/hallucination/score",
            json={"response": response, "retrieved_context": sources, "conversation_id": conv_id},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return float(r.json().get("hallucination_rate", 0.0))
    except Exception as exc:
        logger.warning("Hallucination service error: %s — defaulting to 0.0", exc)
        return 0.0


def _compute_grounding_score(retrieved_sources: List[str]) -> float:
    """
    Simple grounding quality heuristic based on number and length of sources.
    Full score (1.0) requires >= 3 sources each >= 100 chars.
    """
    if not retrieved_sources:
        return 0.0
    qualified = sum(1 for s in retrieved_sources if len(s.strip()) >= 100)
    return min(1.0, qualified / 3.0)


class ResponseScoringService:
    async def score_response(
        self,
        conversation_id: str,
        query: str,
        response: str,
        retrieved_sources: List[str],
        triage_level: str,
    ) -> dict:
        """
        Call all four sub-services concurrently, then compute composite score.
        Returns an EvaluationReport dict.
        """
        async with httpx.AsyncClient() as client:
            triage_task = _call_triage(client, query, triage_level, conversation_id)
            consistency_task = _call_consistency(client, response, retrieved_sources, conversation_id)
            safety_task = _call_safety(client, response, query, triage_level, conversation_id)
            hallucination_task = _call_hallucination(client, response, retrieved_sources, conversation_id)

            triage_score, consistency_score, safety_score, hallucination_rate = await asyncio.gather(
                triage_task, consistency_task, safety_task, hallucination_task
            )

        grounding_score = _compute_grounding_score(retrieved_sources)

        composite_score = (
            W_TRIAGE * triage_score
            + W_CONSISTENCY * consistency_score
            + W_HALLUCINATION * (1.0 - hallucination_rate)
            + W_SAFETY * safety_score
            + W_GROUNDING * grounding_score
        )
        composite_score = round(min(1.0, max(0.0, composite_score)), 4)

        requires_retraining = composite_score < RETRAIN_THRESHOLD

        logger.info(
            "Scoring complete — conv=%s composite=%.4f triage=%.3f consistency=%.3f "
            "safety=%.3f hallucination=%.3f grounding=%.3f retrain=%s",
            conversation_id, composite_score, triage_score, consistency_score,
            safety_score, hallucination_rate, grounding_score, requires_retraining,
        )

        return {
            "conversation_id": conversation_id,
            "composite_score": composite_score,
            "requires_retraining": requires_retraining,
            "component_scores": {
                "triage_accuracy": round(triage_score, 4),
                "medical_consistency": round(consistency_score, 4),
                "hallucination_rate": round(hallucination_rate, 4),
                "safety_score": round(safety_score, 4),
                "grounding_score": round(grounding_score, 4),
            },
            "weights": {
                "triage_accuracy": W_TRIAGE,
                "medical_consistency": W_CONSISTENCY,
                "hallucination_inverted": W_HALLUCINATION,
                "safety": W_SAFETY,
                "grounding": W_GROUNDING,
            },
            "retrain_threshold": RETRAIN_THRESHOLD,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
