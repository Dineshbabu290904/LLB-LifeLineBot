from typing import Optional
import logging

logger = logging.getLogger("triage_accuracy_service")

# Keyword sets for triage classification
EMERGENCY_KEYWORDS = {
    "cardiac arrest", "heart attack", "stroke", "unconscious", "not breathing",
    "choking", "anaphylaxis", "anaphylactic", "severe bleeding", "hemorrhage",
    "chest pain", "difficulty breathing", "shortness of breath", "seizure",
    "overdose", "poisoning", "severe allergic reaction", "loss of consciousness",
    "unresponsive", "collapsed", "no pulse", "cpr", "911", "ambulance",
    "severe head injury", "traumatic injury", "gunshot", "stab wound",
    "diabetic coma", "hypoglycemia severe", "suicidal", "suicide attempt",
}

URGENT_KEYWORDS = {
    "high fever", "fever above 103", "fever above 104", "severe pain",
    "vomiting blood", "blood in stool", "sudden vision loss", "sudden hearing loss",
    "severe headache", "worst headache", "thunderclap headache", "facial droop",
    "arm weakness", "slurred speech", "confusion", "altered mental status",
    "deep cut", "wound won't stop bleeding", "broken bone", "fracture",
    "dislocated", "burns", "chemical exposure", "severe infection",
    "kidney pain", "severe abdominal pain", "appendicitis", "high blood pressure",
    "hypertensive", "severe dehydration", "unable to keep fluids down",
}

NON_URGENT_KEYWORDS = {
    "mild", "slight", "minor", "common cold", "runny nose", "sore throat",
    "mild headache", "mild fever", "low grade fever", "fatigue", "tired",
    "rash", "itching", "constipation", "diarrhea mild", "muscle ache",
    "back pain mild", "joint pain mild", "dry cough", "sneezing",
    "allergy", "seasonal", "ear ache", "toothache", "skin irritation",
}

TRIAGE_LEVELS = ["EMERGENCY", "URGENT", "NON_URGENT", "SELF_CARE"]
LEVEL_SCORES = {"EMERGENCY": 4, "URGENT": 3, "NON_URGENT": 2, "SELF_CARE": 1}


def classify_symptoms(symptoms: str) -> str:
    """Classify symptoms into a triage level based on keyword analysis."""
    text = symptoms.lower()

    for kw in EMERGENCY_KEYWORDS:
        if kw in text:
            return "EMERGENCY"

    for kw in URGENT_KEYWORDS:
        if kw in text:
            return "URGENT"

    for kw in NON_URGENT_KEYWORDS:
        if kw in text:
            return "NON_URGENT"

    return "SELF_CARE"


def compute_accuracy_score(expected: str, actual: str) -> float:
    """
    Score accuracy — exact match = 1.0, one level off = 0.5,
    two levels off = 0.25, larger gaps = 0.0.
    Especially penalise under-triaging emergencies.
    """
    if expected == actual:
        return 1.0

    exp_score = LEVEL_SCORES.get(expected, 0)
    act_score = LEVEL_SCORES.get(actual, 0)
    diff = abs(exp_score - act_score)

    # Under-triaging an emergency (calling EMERGENCY → something lower) is worst case
    if expected == "EMERGENCY" and act_score < exp_score:
        return 0.0

    if diff == 1:
        return 0.5
    if diff == 2:
        return 0.25
    return 0.0


class TriageAccuracyService:
    def validate(
        self,
        symptoms: str,
        actual_level: str,
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Validate a triage decision against symptom analysis."""
        actual_level = actual_level.upper()
        if actual_level not in TRIAGE_LEVELS:
            return {
                "error": f"Unknown triage level: {actual_level}. Must be one of {TRIAGE_LEVELS}",
                "conversation_id": conversation_id,
            }

        expected_level = classify_symptoms(symptoms)
        accuracy_score = compute_accuracy_score(expected_level, actual_level)
        is_accurate = accuracy_score >= 0.5

        reasoning = self._build_reasoning(symptoms, expected_level, actual_level, accuracy_score)

        logger.info(
            "Triage validation — conversation=%s expected=%s actual=%s score=%.2f",
            conversation_id, expected_level, actual_level, accuracy_score,
        )

        return {
            "conversation_id": conversation_id,
            "is_accurate": is_accurate,
            "expected_level": expected_level,
            "actual_level": actual_level,
            "accuracy_score": accuracy_score,
            "reasoning": reasoning,
        }

    def _build_reasoning(
        self, symptoms: str, expected: str, actual: str, score: float
    ) -> str:
        if expected == actual:
            return f"Triage level '{actual}' matches the expected classification based on symptom analysis."
        direction = "under-triaged" if LEVEL_SCORES[actual] < LEVEL_SCORES[expected] else "over-triaged"
        return (
            f"Based on symptom analysis, '{expected}' was expected but '{actual}' was assigned. "
            f"The response was {direction} (score={score:.2f}). "
            f"Symptom snippet: '{symptoms[:120]}...'"
        )

    def compute_batch_accuracy(self, records: list[dict]) -> dict:
        """
        Compute accuracy over a batch of validation records.
        Each record: {symptoms, actual_level, conversation_id (optional)}
        """
        if not records:
            return {"error": "Empty batch", "total": 0, "accuracy": 0.0}

        results = [self.validate(**r) for r in records]
        scores = [r["accuracy_score"] for r in results if "accuracy_score" in r]
        valid_count = len(scores)
        mean_accuracy = sum(scores) / valid_count if valid_count else 0.0

        level_breakdown: dict[str, dict] = {}
        for r in results:
            if "expected_level" not in r:
                continue
            lvl = r["expected_level"]
            if lvl not in level_breakdown:
                level_breakdown[lvl] = {"total": 0, "correct": 0}
            level_breakdown[lvl]["total"] += 1
            if r["is_accurate"]:
                level_breakdown[lvl]["correct"] += 1

        return {
            "total": len(records),
            "valid": valid_count,
            "mean_accuracy": round(mean_accuracy, 4),
            "level_breakdown": level_breakdown,
            "results": results,
        }
