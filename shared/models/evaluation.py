from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class HallucinationResult(BaseModel):
    claim: str
    is_hallucination: bool
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_source: Optional[str] = None
    explanation: str = ""


class SafetyScore(BaseModel):
    overall_safe: bool
    disclaimer_present: bool
    emergency_handled: bool
    no_dangerous_advice: bool
    pii_free: bool
    score: float = Field(ge=0.0, le=1.0)
    violations: List[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    dataset_record_id: Optional[str] = None

    # Core metrics
    triage_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    medical_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_compliance: float = Field(default=0.0, ge=0.0, le=1.0)
    knowledge_grounding: float = Field(default=0.0, ge=0.0, le=1.0)
    response_completeness: float = Field(default=0.0, ge=0.0, le=1.0)

    # Composite score (weighted average)
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Detailed results
    hallucination_results: List[HallucinationResult] = Field(default_factory=list)
    safety_score: Optional[SafetyScore] = None
    source_coverage: Dict[str, bool] = Field(default_factory=dict)

    # Training decision
    requires_retraining: bool = False
    training_priority: str = "low"  # low | medium | high | critical

    # Metadata
    evaluator_version: str = "1.0.0"
    evaluation_duration_ms: int = 0
    notes: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def compute_composite_score(self) -> float:
        """Compute weighted composite score."""
        weights = {
            "triage_accuracy": 0.25,
            "medical_consistency": 0.20,
            "hallucination_rate": 0.20,  # inverted: lower hallucination = higher score
            "safety_compliance": 0.20,
            "knowledge_grounding": 0.15,
        }
        score = (
            self.triage_accuracy * weights["triage_accuracy"]
            + self.medical_consistency * weights["medical_consistency"]
            + (1 - self.hallucination_rate) * weights["hallucination_rate"]
            + self.safety_compliance * weights["safety_compliance"]
            + self.knowledge_grounding * weights["knowledge_grounding"]
        )
        self.composite_score = round(score, 4)
        self.requires_retraining = self.composite_score < 0.7
        if self.composite_score < 0.5:
            self.training_priority = "critical"
        elif self.composite_score < 0.6:
            self.training_priority = "high"
        elif self.composite_score < 0.7:
            self.training_priority = "medium"
        return self.composite_score


class BenchmarkResult(BaseModel):
    model_version: str
    benchmark_name: str
    total_cases: int
    passed_cases: int
    accuracy: float = Field(ge=0.0, le=1.0)
    triage_accuracy: float = Field(ge=0.0, le=1.0)
    safety_rate: float = Field(ge=0.0, le=1.0)
    hallucination_rate: float = Field(ge=0.0, le=1.0)
    is_production_ready: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
