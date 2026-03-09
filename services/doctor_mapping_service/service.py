"""Doctor Mapping Service - maps symptoms/conditions to medical specialties."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    class Config:
        env_prefix = "DOCTOR_MAPPING_"

settings = Settings()

SPECIALTY_KEYWORDS: Dict[str, List[str]] = {
    "cardiology": ["heart", "chest pain", "palpitations", "hypertension", "cardiac", "arrhythmia", "coronary"],
    "pulmonology": ["lungs", "breathing", "asthma", "copd", "cough", "dyspnea", "pneumonia", "respiratory"],
    "neurology": ["brain", "stroke", "seizure", "headache", "migraine", "tremor", "paralysis", "dizziness"],
    "gastroenterology": ["stomach", "abdomen", "diarrhea", "constipation", "nausea", "vomiting", "liver", "colon"],
    "endocrinology": ["diabetes", "thyroid", "insulin", "hormone", "metabolic", "obesity", "adrenal"],
    "orthopedics": ["bone", "joint", "fracture", "arthritis", "spine", "back pain", "knee", "hip"],
    "dermatology": ["skin", "rash", "acne", "eczema", "psoriasis", "lesion", "wound", "dermatitis"],
    "ophthalmology": ["eye", "vision", "blindness", "cataract", "glaucoma", "retina"],
    "otolaryngology": ["ear", "nose", "throat", "hearing", "sinusitis", "tonsil", "ENT"],
    "urology": ["urinary", "kidney", "bladder", "prostate", "UTI", "renal"],
    "gynecology": ["menstrual", "ovary", "uterus", "pregnancy", "vaginal", "cervical", "pelvic"],
    "psychiatry": ["anxiety", "depression", "mental", "mood", "psychosis", "bipolar", "OCD", "PTSD"],
    "pediatrics": ["child", "infant", "baby", "growth", "development", "vaccination"],
    "oncology": ["cancer", "tumor", "malignancy", "chemotherapy", "biopsy", "metastasis"],
    "infectious_disease": ["infection", "fever", "virus", "bacteria", "sepsis", "HIV", "tuberculosis"],
    "rheumatology": ["autoimmune", "lupus", "rheumatoid", "fibromyalgia", "gout", "inflammation"],
    "nephrology": ["kidney disease", "dialysis", "glomerulonephritis", "proteinuria", "creatinine"],
    "hematology": ["blood", "anemia", "clotting", "leukemia", "platelet", "hemophilia"],
    "emergency_medicine": ["emergency", "trauma", "critical", "accident", "overdose", "acute"],
    "general_practice": ["general", "checkup", "preventive", "routine", "common cold", "flu"],
}

SPECIALTY_INFO: Dict[str, Dict[str, str]] = {
    "cardiology": {"description": "Heart and cardiovascular system specialist", "urgency_default": "urgent"},
    "pulmonology": {"description": "Lung and respiratory system specialist", "urgency_default": "semi-urgent"},
    "neurology": {"description": "Brain and nervous system specialist", "urgency_default": "urgent"},
    "gastroenterology": {"description": "Digestive system specialist", "urgency_default": "routine"},
    "endocrinology": {"description": "Hormonal and metabolic disorder specialist", "urgency_default": "routine"},
    "orthopedics": {"description": "Bone and joint specialist", "urgency_default": "semi-urgent"},
    "dermatology": {"description": "Skin condition specialist", "urgency_default": "routine"},
    "ophthalmology": {"description": "Eye and vision specialist", "urgency_default": "semi-urgent"},
    "otolaryngology": {"description": "Ear, nose, throat specialist (ENT)", "urgency_default": "routine"},
    "urology": {"description": "Urinary tract and male reproductive specialist", "urgency_default": "routine"},
    "gynecology": {"description": "Female reproductive system specialist", "urgency_default": "routine"},
    "psychiatry": {"description": "Mental health specialist", "urgency_default": "semi-urgent"},
    "pediatrics": {"description": "Children's health specialist", "urgency_default": "semi-urgent"},
    "oncology": {"description": "Cancer specialist", "urgency_default": "urgent"},
    "infectious_disease": {"description": "Infectious disease specialist", "urgency_default": "urgent"},
    "rheumatology": {"description": "Autoimmune and inflammatory disease specialist", "urgency_default": "routine"},
    "nephrology": {"description": "Kidney disease specialist", "urgency_default": "semi-urgent"},
    "hematology": {"description": "Blood disorder specialist", "urgency_default": "urgent"},
    "emergency_medicine": {"description": "Emergency and acute care specialist", "urgency_default": "emergency"},
    "general_practice": {"description": "Primary care and general health", "urgency_default": "routine"},
}


class DoctorMappingService:
    async def startup(self):
        logger.info("DoctorMappingService started")

    async def shutdown(self):
        pass

    def map_to_specialty(self, symptoms: List[str], additional_context: str = "") -> Dict[str, Any]:
        text = " ".join(symptoms) + " " + additional_context
        text_lower = text.lower()

        scores: Dict[str, float] = {}
        for specialty, keywords in SPECIALTY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                scores[specialty] = matches / len(keywords)

        if not scores:
            primary = "general_practice"
            alternatives = []
        else:
            sorted_specs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_specs[0][0]
            alternatives = [s for s, _ in sorted_specs[1:4]]

        info = SPECIALTY_INFO.get(primary, {})
        return {
            "primary_specialty": primary,
            "description": info.get("description", ""),
            "urgency": info.get("urgency_default", "routine"),
            "alternative_specialties": alternatives,
            "confidence": scores.get(primary, 0.5),
            "matched_symptoms": symptoms,
        }

    def list_specialties(self) -> List[Dict[str, Any]]:
        return [
            {"specialty": name, **info}
            for name, info in SPECIALTY_INFO.items()
        ]
