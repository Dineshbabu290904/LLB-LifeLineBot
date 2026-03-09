import os
from typing import Dict, Any

# Centralized service configuration registry
SERVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "default": {
        "mongo_url": os.getenv("MONGO_URL", "mongodb://mongodb:27017"),
        "mongo_db_name": os.getenv("MONGO_DB_NAME", "medbot"),
        "redis_url": os.getenv("REDIS_URL", "redis://redis:6379"),
        "postgres_url": os.getenv("POSTGRES_URL", "postgresql://medbot_user:medbot_pass@postgresql:5432/medbot"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "environment": os.getenv("ENVIRONMENT", "development"),
    },
    "langgraph_orchestrator": {
        "max_retries": 3,
        "timeout_seconds": 120,
        "hallucination_threshold": 0.3,
        "quality_threshold": 0.7,
    },
    "vector_index_service": {
        "faiss_index_path": "/data/faiss_index",
        "faiss_dimension": 384,
        "faiss_top_k": 5,
    },
    "training_pipeline_service": {
        "retrain_dataset_size": 1000,
        "min_quality_score": 0.7,
        "lora_rank": 8,
        "lora_alpha": 32,
    },
    "rate_limit_service": {
        "requests_per_minute": 100,
        "window_seconds": 60,
    },
}


class ConfigService:
    def get_config(self, service_name: str) -> Dict[str, Any]:
        config = SERVICE_CONFIGS.get("default", {}).copy()
        config.update(SERVICE_CONFIGS.get(service_name, {}))
        config["service_name"] = service_name
        return config

    def get_all_configs(self) -> Dict[str, Any]:
        return SERVICE_CONFIGS
