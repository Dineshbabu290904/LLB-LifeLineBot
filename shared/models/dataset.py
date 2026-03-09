from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class DatasetTag(str, Enum):
    SYMPTOM_QUERY = "symptom_query"
    DIAGNOSIS = "diagnosis"
    TRIAGE = "triage"
    DOCTOR_RECOMMENDATION = "doctor_recommendation"
    MEDICATION_QUERY = "medication_query"
    EMERGENCY = "emergency"
    ROUTINE = "routine"
    MULTIMODAL = "multimodal"
    FOLLOW_UP = "follow_up"


class TrainingExample(BaseModel):
    input: str
    output: str
    reasoning: Optional[str] = None
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class DatasetRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    session_id: str

    # Core training data
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_query: str
    assistant_response: str

    # Medical structured data
    symptoms_extracted: List[Dict[str, Any]] = Field(default_factory=list)
    diagnosis_reasoning: str = ""
    severity_classification: str = ""
    triage_level: str = ""
    doctor_recommendation: Optional[Dict[str, Any]] = None

    # Knowledge and sources
    knowledge_sources: List[str] = Field(default_factory=list)
    retrieved_context: List[str] = Field(default_factory=list)

    # Training metadata
    training_tags: List[DatasetTag] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    has_image: bool = False
    is_emergency: bool = False
    is_validated: bool = False

    # Evaluation results
    hallucination_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_compliant: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_training_example(self) -> TrainingExample:
        """Convert to a simple training example format."""
        input_text = f"Patient query: {self.user_query}"
        if self.symptoms_extracted:
            symptom_names = [s.get("name", "") for s in self.symptoms_extracted]
            input_text += f"\nSymptoms: {', '.join(symptom_names)}"

        return TrainingExample(
            input=input_text,
            output=self.assistant_response,
            reasoning=self.diagnosis_reasoning,
            quality_score=self.quality_score,
        )


class DatasetBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    records: List[DatasetRecord] = Field(default_factory=list)
    total_count: int = 0
    quality_threshold: float = 0.7
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def filter_by_quality(self, threshold: float = None) -> "DatasetBatch":
        t = threshold or self.quality_threshold
        filtered = [r for r in self.records if r.quality_score >= t]
        return DatasetBatch(
            records=filtered,
            total_count=len(filtered),
            quality_threshold=t,
        )
