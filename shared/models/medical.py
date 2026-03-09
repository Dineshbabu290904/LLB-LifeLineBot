from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TriageLevel(str, Enum):
    EMERGENCY = "EMERGENCY"       # Call 911 / immediate ER
    URGENT = "URGENT"             # See doctor within 24h
    SEMI_URGENT = "SEMI_URGENT"   # See doctor within 48-72h
    ROUTINE = "ROUTINE"           # Schedule appointment
    SELF_CARE = "SELF_CARE"       # Home management with monitoring


class MedicalSpecialty(str, Enum):
    EMERGENCY_MEDICINE = "Emergency Medicine"
    CARDIOLOGY = "Cardiology"
    NEUROLOGY = "Neurology"
    PULMONOLOGY = "Pulmonology"
    GASTROENTEROLOGY = "Gastroenterology"
    ORTHOPEDICS = "Orthopedics"
    DERMATOLOGY = "Dermatology"
    PSYCHIATRY = "Psychiatry"
    ENDOCRINOLOGY = "Endocrinology"
    NEPHROLOGY = "Nephrology"
    ONCOLOGY = "Oncology"
    GENERAL_PRACTICE = "General Practice"
    PEDIATRICS = "Pediatrics"
    GYNECOLOGY = "Gynecology"
    UROLOGY = "Urology"
    OPHTHALMOLOGY = "Ophthalmology"
    ENT = "ENT (Ear, Nose, Throat)"
    RHEUMATOLOGY = "Rheumatology"
    INFECTIOUS_DISEASE = "Infectious Disease"
    HEMATOLOGY = "Hematology"


class Symptom(BaseModel):
    name: str
    severity: str = Field(default="moderate", description="mild | moderate | severe")
    duration: Optional[str] = None
    location: Optional[str] = None
    onset: Optional[str] = None
    aggravating_factors: List[str] = Field(default_factory=list)
    relieving_factors: List[str] = Field(default_factory=list)
    associated_symptoms: List[str] = Field(default_factory=list)


class MedicalEntity(BaseModel):
    entity_type: str  # symptom | medication | condition | procedure | anatomy
    name: str
    normalized_name: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None


class Diagnosis(BaseModel):
    condition: str
    icd10_code: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str
    supporting_evidence: List[str] = Field(default_factory=list)
    differential_diagnoses: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="This is not a medical diagnosis. Please consult a licensed healthcare professional."
    )


class DoctorRecommendation(BaseModel):
    specialty: MedicalSpecialty
    urgency: TriageLevel
    reasoning: str
    alternative_specialties: List[MedicalSpecialty] = Field(default_factory=list)
    telehealth_appropriate: bool = False
    emergency_services: bool = False
    estimated_wait_time: Optional[str] = None


class RiskAssessment(BaseModel):
    risk_level: str  # low | medium | high | critical
    red_flags: List[str] = Field(default_factory=list)
    emergency_indicators: List[str] = Field(default_factory=list)
    requires_immediate_attention: bool = False
    reasoning: str = ""


class MedicalResponse(BaseModel):
    response_text: str
    triage_level: TriageLevel
    symptoms_identified: List[Symptom] = Field(default_factory=list)
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    doctor_recommendation: Optional[DoctorRecommendation] = None
    risk_assessment: Optional[RiskAssessment] = None
    sources: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default=(
            "\n\n⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
            "and does not constitute medical advice. Always consult a qualified healthcare "
            "professional for medical decisions. In case of emergency, call emergency services immediately."
        )
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
