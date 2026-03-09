from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "MEDBOT"
    app_version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # MongoDB
    mongo_url: str = Field(default="mongodb://mongodb:27017")
    mongo_db_name: str = Field(default="medbot")

    # PostgreSQL
    postgres_url: str = Field(
        default="postgresql://medbot_user:medbot_pass@postgresql:5432/medbot"
    )

    # Redis
    redis_url: str = Field(default="redis://redis:6379")
    redis_ttl_seconds: int = Field(default=3600)

    # Ollama
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_reasoning_model: str = Field(default="llama3.2:latest")
    ollama_vision_model: str = Field(default="llava:latest")
    ollama_embedding_model: str = Field(default="nomic-embed-text:latest")
    ollama_classification_model: str = Field(default="phi3:mini")

    # FAISS
    faiss_index_path: str = Field(default="/data/faiss_index")
    faiss_dimension: int = Field(default=384)
    faiss_top_k: int = Field(default=5)

    # JWT Auth
    jwt_secret_key: str = Field(default="medbot-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # Service URLs (internal Docker DNS)
    config_service_url: str = Field(default="http://config_service:8090")
    logging_service_url: str = Field(default="http://logging_service:8091")
    monitoring_service_url: str = Field(default="http://monitoring_service:8092")
    metrics_service_url: str = Field(default="http://metrics_service:8093")

    auth_service_url: str = Field(default="http://auth_service:8001")
    session_service_url: str = Field(default="http://session_service:8002")
    rate_limit_service_url: str = Field(default="http://rate_limit_service:8003")
    request_validation_service_url: str = Field(default="http://request_validation_service:8004")

    langgraph_orchestrator_url: str = Field(default="http://langgraph_orchestrator:8010")
    agent_controller_url: str = Field(default="http://agent_controller:8011")

    conversation_storage_url: str = Field(default="http://conversation_storage_service:8040")
    dataset_storage_url: str = Field(default="http://dataset_storage_service:8041")
    metadata_storage_url: str = Field(default="http://metadata_storage_service:8042")
    audit_log_url: str = Field(default="http://audit_log_service:8043")
    knowledge_base_url: str = Field(default="http://knowledge_base_service:8044")

    ollama_router_url: str = Field(default="http://ollama_router_service:8050")
    reasoning_model_url: str = Field(default="http://reasoning_model_service:8051")
    embedding_model_url: str = Field(default="http://embedding_model_service:8052")
    vision_model_url: str = Field(default="http://vision_model_service:8053")
    classification_model_url: str = Field(default="http://classification_model_service:8054")

    document_ingestion_url: str = Field(default="http://document_ingestion_service:8060")
    document_cleaning_url: str = Field(default="http://document_cleaning_service:8061")
    document_chunking_url: str = Field(default="http://document_chunking_service:8062")
    embedding_generation_url: str = Field(default="http://embedding_generation_service:8063")
    vector_index_url: str = Field(default="http://vector_index_service:8064")
    vector_search_url: str = Field(default="http://vector_search_service:8065")
    context_builder_url: str = Field(default="http://context_builder_service:8066")

    medical_entity_extraction_url: str = Field(default="http://medical_entity_extraction_service:8070")
    severity_classification_url: str = Field(default="http://severity_classification_service:8071")
    risk_detection_url: str = Field(default="http://risk_detection_service:8072")
    emergency_detection_url: str = Field(default="http://emergency_detection_service:8073")
    doctor_mapping_url: str = Field(default="http://doctor_mapping_service:8074")

    web_search_url: str = Field(default="http://web_search_service:8080")
    pubmed_search_url: str = Field(default="http://pubmed_search_service:8081")
    who_guidelines_url: str = Field(default="http://who_guidelines_service:8082")
    medical_source_validation_url: str = Field(default="http://medical_source_validation_service:8083")

    symptom_extraction_agent_url: str = Field(default="http://symptom_extraction_agent:8020")
    rag_agent_url: str = Field(default="http://rag_agent_service:8021")
    reasoning_agent_url: str = Field(default="http://reasoning_agent_service:8022")
    vision_agent_url: str = Field(default="http://vision_agent_service:8023")
    triage_agent_url: str = Field(default="http://triage_agent:8024")
    doctor_recommendation_agent_url: str = Field(default="http://doctor_recommendation_agent:8025")
    hallucination_detection_agent_url: str = Field(default="http://hallucination_detection_agent:8026")
    safety_guardrail_agent_url: str = Field(default="http://safety_guardrail_agent:8027")
    dataset_generation_agent_url: str = Field(default="http://dataset_generation_agent:8028")
    evaluation_agent_url: str = Field(default="http://evaluation_agent:8029")

    response_scoring_url: str = Field(default="http://response_scoring_service:8100")
    triage_accuracy_url: str = Field(default="http://triage_accuracy_service:8101")
    medical_consistency_url: str = Field(default="http://medical_consistency_service:8102")
    safety_validation_url: str = Field(default="http://safety_validation_service:8103")

    dataset_preparation_url: str = Field(default="http://dataset_preparation_service:8110")
    training_pipeline_url: str = Field(default="http://training_pipeline_service:8111")
    fine_tuning_url: str = Field(default="http://fine_tuning_service:8112")
    model_registry_url: str = Field(default="http://model_registry_service:8113")
    model_versioning_url: str = Field(default="http://model_versioning_service:8114")

    # PubMed API
    pubmed_api_key: Optional[str] = Field(default=None)
    pubmed_base_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils")

    # Safety thresholds
    hallucination_threshold: float = Field(default=0.3)
    quality_threshold: float = Field(default=0.7)
    retrain_dataset_size: int = Field(default=1000)

    # Rate limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window_seconds: int = Field(default=60)

    # Chunk settings
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=50)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
