import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class OrchestratorConfig(BaseSettings):
    service_name: str = "langgraph_orchestrator"
    port: int = 8010
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "medbot")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Service URLs
    symptom_extraction_url: str = os.getenv("SYMPTOM_EXTRACTION_URL", "http://symptom_extraction_agent:8020")
    rag_agent_url: str = os.getenv("RAG_AGENT_URL", "http://rag_agent_service:8021")
    reasoning_agent_url: str = os.getenv("REASONING_AGENT_URL", "http://reasoning_agent_service:8022")
    vision_agent_url: str = os.getenv("VISION_AGENT_URL", "http://vision_agent_service:8023")
    triage_agent_url: str = os.getenv("TRIAGE_AGENT_URL", "http://triage_agent:8024")
    doctor_recommendation_url: str = os.getenv("DOCTOR_RECOMMENDATION_URL", "http://doctor_recommendation_agent:8025")
    hallucination_detection_url: str = os.getenv("HALLUCINATION_DETECTION_URL", "http://hallucination_detection_agent:8026")
    safety_guardrail_url: str = os.getenv("SAFETY_GUARDRAIL_URL", "http://safety_guardrail_agent:8027")
    dataset_generation_url: str = os.getenv("DATASET_GENERATION_URL", "http://dataset_generation_agent:8028")
    evaluation_agent_url: str = os.getenv("EVALUATION_AGENT_URL", "http://evaluation_agent:8029")
    search_agent_url: str = os.getenv("SEARCH_AGENT_URL", "http://search_agent_service:8030")
    knowledge_agent_url: str = os.getenv("KNOWLEDGE_AGENT_URL", "http://knowledge_agent_service:8031")
    conversation_storage_url: str = os.getenv("CONVERSATION_STORAGE_URL", "http://conversation_storage_service:8040")

    # Pipeline settings
    max_retries: int = 3
    hallucination_threshold: float = 0.3
    min_context_chunks: int = 2
    pipeline_timeout_seconds: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_config() -> OrchestratorConfig:
    return OrchestratorConfig()
