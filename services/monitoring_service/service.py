import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import httpx
import logging

logger = logging.getLogger("monitoring_service")

HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "5.0"))

# Registry of every MEDBOT service and its health endpoint base URL.
# URLs are resolved via Docker Compose service names by default; override
# individual entries with environment variables for non-default deployments.
SERVICE_REGISTRY: Dict[str, str] = {
    "api_gateway":                    os.getenv("API_GATEWAY_URL",                    "http://api_gateway:8000"),
    "agent_controller":               os.getenv("AGENT_CONTROLLER_URL",               "http://agent_controller:8001"),
    "triage_agent":                   os.getenv("TRIAGE_AGENT_URL",                   "http://triage_agent:8010"),
    "symptom_extraction_agent":       os.getenv("SYMPTOM_EXTRACTION_AGENT_URL",       "http://symptom_extraction_agent:8011"),
    "doctor_recommendation_agent":    os.getenv("DOCTOR_RECOMMENDATION_AGENT_URL",    "http://doctor_recommendation_agent:8012"),
    "safety_guardrail_agent":         os.getenv("SAFETY_GUARDRAIL_AGENT_URL",         "http://safety_guardrail_agent:8013"),
    "hallucination_detection_agent":  os.getenv("HALLUCINATION_DETECTION_AGENT_URL",  "http://hallucination_detection_agent:8014"),
    "rag_agent_service":              os.getenv("RAG_AGENT_SERVICE_URL",              "http://rag_agent_service:8015"),
    "evaluation_agent":               os.getenv("EVALUATION_AGENT_URL",               "http://evaluation_agent:8016"),
    "search_agent_service":           os.getenv("SEARCH_AGENT_SERVICE_URL",           "http://search_agent_service:8017"),
    "reasoning_agent_service":        os.getenv("REASONING_AGENT_SERVICE_URL",        "http://reasoning_agent_service:8018"),
    "vision_agent_service":           os.getenv("VISION_AGENT_SERVICE_URL",           "http://vision_agent_service:8019"),
    "knowledge_agent_service":        os.getenv("KNOWLEDGE_AGENT_SERVICE_URL",        "http://knowledge_agent_service:8020"),
    "dataset_generation_agent":       os.getenv("DATASET_GENERATION_AGENT_URL",       "http://dataset_generation_agent:8021"),
    "langgraph_orchestrator":         os.getenv("LANGGRAPH_ORCHESTRATOR_URL",         "http://langgraph_orchestrator:8030"),
    "session_service":                os.getenv("SESSION_SERVICE_URL",                "http://session_service:8031"),
    "context_builder_service":        os.getenv("CONTEXT_BUILDER_SERVICE_URL",        "http://context_builder_service:8032"),
    "rate_limit_service":             os.getenv("RATE_LIMIT_SERVICE_URL",             "http://rate_limit_service:8033"),
    "request_validation_service":     os.getenv("REQUEST_VALIDATION_SERVICE_URL",     "http://request_validation_service:8034"),
    "auth_service":                   os.getenv("AUTH_SERVICE_URL",                   "http://auth_service:8035"),
    "config_service":                 os.getenv("CONFIG_SERVICE_URL",                 "http://config_service:8036"),
    "conversation_storage_service":   os.getenv("CONVERSATION_STORAGE_URL",           "http://conversation_storage_service:8040"),
    "dataset_storage_service":        os.getenv("DATASET_STORAGE_URL",               "http://dataset_storage_service:8041"),
    "metadata_storage_service":       os.getenv("METADATA_STORAGE_URL",              "http://metadata_storage_service:8042"),
    "audit_log_service":              os.getenv("AUDIT_LOG_URL",                      "http://audit_log_service:8043"),
    "knowledge_base_service":         os.getenv("KNOWLEDGE_BASE_URL",                 "http://knowledge_base_service:8044"),
    "embedding_generation_service":   os.getenv("EMBEDDING_GENERATION_URL",           "http://embedding_generation_service:8050"),
    "vector_index_service":           os.getenv("VECTOR_INDEX_URL",                   "http://vector_index_service:8051"),
    "vector_search_service":          os.getenv("VECTOR_SEARCH_URL",                  "http://vector_search_service:8052"),
    "document_ingestion_service":     os.getenv("DOCUMENT_INGESTION_URL",             "http://document_ingestion_service:8053"),
    "document_chunking_service":      os.getenv("DOCUMENT_CHUNKING_URL",              "http://document_chunking_service:8054"),
    "document_cleaning_service":      os.getenv("DOCUMENT_CLEANING_URL",              "http://document_cleaning_service:8055"),
    "pubmed_search_service":          os.getenv("PUBMED_SEARCH_URL",                  "http://pubmed_search_service:8056"),
    "who_guidelines_service":         os.getenv("WHO_GUIDELINES_URL",                 "http://who_guidelines_service:8057"),
    "web_search_service":             os.getenv("WEB_SEARCH_URL",                     "http://web_search_service:8058"),
    "medical_source_validation_service": os.getenv("MEDICAL_SOURCE_VALIDATION_URL",  "http://medical_source_validation_service:8059"),
    "ollama_router_service":          os.getenv("OLLAMA_ROUTER_URL",                  "http://ollama_router_service:8060"),
    "embedding_model_service":        os.getenv("EMBEDDING_MODEL_URL",               "http://embedding_model_service:8061"),
    "classification_model_service":   os.getenv("CLASSIFICATION_MODEL_URL",           "http://classification_model_service:8062"),
    "reasoning_model_service":        os.getenv("REASONING_MODEL_URL",               "http://reasoning_model_service:8063"),
    "vision_model_service":           os.getenv("VISION_MODEL_URL",                  "http://vision_model_service:8064"),
    "dataset_labeling_model_service": os.getenv("DATASET_LABELING_MODEL_URL",        "http://dataset_labeling_model_service:8065"),
    "model_registry_service":         os.getenv("MODEL_REGISTRY_URL",               "http://model_registry_service:8070"),
    "model_versioning_service":       os.getenv("MODEL_VERSIONING_URL",              "http://model_versioning_service:8071"),
    "fine_tuning_service":            os.getenv("FINE_TUNING_URL",                   "http://fine_tuning_service:8072"),
    "training_pipeline_service":      os.getenv("TRAINING_PIPELINE_URL",             "http://training_pipeline_service:8073"),
    "dataset_preparation_service":    os.getenv("DATASET_PREPARATION_URL",           "http://dataset_preparation_service:8074"),
    "safety_validation_service":      os.getenv("SAFETY_VALIDATION_URL",             "http://safety_validation_service:8080"),
    "hallucination_detection_service":os.getenv("HALLUCINATION_DETECTION_URL",       "http://hallucination_detection_service:8081"),
    "medical_consistency_service":    os.getenv("MEDICAL_CONSISTENCY_URL",           "http://medical_consistency_service:8082"),
    "risk_detection_service":         os.getenv("RISK_DETECTION_URL",               "http://risk_detection_service:8083"),
    "emergency_detection_service":    os.getenv("EMERGENCY_DETECTION_URL",           "http://emergency_detection_service:8084"),
    "response_scoring_service":       os.getenv("RESPONSE_SCORING_URL",              "http://response_scoring_service:8085"),
    "medical_entity_extraction_service": os.getenv("MEDICAL_ENTITY_EXTRACTION_URL",  "http://medical_entity_extraction_service:8086"),
    "severity_classification_service":os.getenv("SEVERITY_CLASSIFICATION_URL",       "http://severity_classification_service:8087"),
    "triage_accuracy_service":        os.getenv("TRIAGE_ACCURACY_URL",              "http://triage_accuracy_service:8088"),
    "doctor_mapping_service":         os.getenv("DOCTOR_MAPPING_URL",               "http://doctor_mapping_service:8089"),
    "logging_service":                os.getenv("LOGGING_SERVICE_URL",               "http://logging_service:8091"),
    "metrics_service":                os.getenv("METRICS_SERVICE_URL",               "http://metrics_service:8093"),
}


async def poll_service(name: str, base_url: str, client: httpx.AsyncClient) -> dict:
    """Poll a single service /health endpoint and return a structured result."""
    url = f"{base_url}/health"
    try:
        resp = await client.get(url, timeout=HEALTH_TIMEOUT)
        body = {}
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:200]}
        return {
            "service": name,
            "url": url,
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "http_status": resp.status_code,
            "response": body,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.TimeoutException:
        return {
            "service": name,
            "url": url,
            "status": "timeout",
            "http_status": None,
            "response": {"error": "Connection timed out"},
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "service": name,
            "url": url,
            "status": "unreachable",
            "http_status": None,
            "response": {"error": str(exc)},
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


async def check_all_services() -> dict:
    """Poll all registered services concurrently and return aggregated report."""
    async with httpx.AsyncClient() as client:
        tasks = [
            poll_service(name, url, client)
            for name, url in SERVICE_REGISTRY.items()
        ]
        results = await asyncio.gather(*tasks)

    healthy = [r for r in results if r["status"] == "healthy"]
    degraded = [r for r in results if r["status"] == "degraded"]
    unreachable = [r for r in results if r["status"] in ("unreachable", "timeout")]

    return {
        "summary": {
            "total": len(results),
            "healthy": len(healthy),
            "degraded": len(degraded),
            "unreachable": len(unreachable),
            "overall": "healthy" if len(unreachable) == 0 and len(degraded) == 0 else "degraded",
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "services": results,
    }


async def check_single_service(service_name: str) -> Optional[dict]:
    """Poll a single named service. Returns None if service not in registry."""
    base_url = SERVICE_REGISTRY.get(service_name)
    if not base_url:
        return None
    async with httpx.AsyncClient() as client:
        return await poll_service(service_name, base_url, client)
