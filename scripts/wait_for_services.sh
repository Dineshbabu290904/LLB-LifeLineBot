#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Wait for all 59 MEDBOT microservices to be healthy before running tests.
# Usage: ./scripts/wait_for_services.sh [--timeout 120]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MAX_WAIT=${1:-120}   # total seconds to wait
INTERVAL=5
BASE_URL="http://localhost"

# All services: name:port
SERVICES=(
  "api_gateway:8000"
  "auth_service:8001"
  "session_service:8002"
  "rate_limit_service:8003"
  "request_validation_service:8004"
  "agent_controller:8005"
  "langgraph_orchestrator:8010"
  "triage_agent:8015"
  "context_builder_service:8020"
  "knowledge_agent_service:8021"
  "knowledge_base_service:8022"
  "vision_agent_service:8023"
  "rag_agent_service:8025"
  "reasoning_agent_service:8026"
  "safety_guardrail_agent:8027"
  "search_agent_service:8028"
  "evaluation_agent:8029"
  "dataset_generation_agent:8030"
  "dataset_labeling_model_service:8031"
  "dataset_preparation_service:8032"
  "conversation_storage_service:8040"
  "dataset_storage_service:8041"
  "metadata_storage_service:8042"
  "audit_log_service:8043"
  "ollama_router_service:8050"
  "reasoning_model_service:8051"
  "embedding_model_service:8052"
  "vision_model_service:8053"
  "embedding_generation_service:8054"
  "vector_index_service:8055"
  "vector_search_service:8056"
  "classification_model_service:8057"
  "response_scoring_service:8058"
  "document_ingestion_service:8060"
  "document_chunking_service:8061"
  "document_cleaning_service:8062"
  "medical_entity_extraction_service:8070"
  "severity_classification_service:8071"
  "emergency_detection_service:8072"
  "medical_source_validation_service:8073"
  "pubmed_search_service:8074"
  "risk_detection_service:8075"
  "symptom_extraction_agent:8076"
  "web_search_service:8077"
  "who_guidelines_service:8078"
  "doctor_mapping_service:8080"
  "doctor_recommendation_agent:8081"
  "config_service:8090"
  "logging_service:8091"
  "monitoring_service:8092"
  "metrics_service:8093"
  "triage_accuracy_service:8101"
  "medical_consistency_service:8102"
  "safety_validation_service:8103"
  "hallucination_detection_agent:8104"
  "fine_tuning_service:8110"
  "training_pipeline_service:8111"
  "model_registry_service:8120"
  "model_versioning_service:8121"
)

is_healthy() {
  local port=$1
  curl -sf --max-time 3 "${BASE_URL}:${port}/health" > /dev/null 2>&1
}

echo "Waiting for all ${#SERVICES[@]} services to be healthy (timeout: ${MAX_WAIT}s)..."
elapsed=0

while true; do
  not_ready=()
  for svc in "${SERVICES[@]}"; do
    port="${svc##*:}"
    name="${svc%%:*}"
    if ! is_healthy "$port"; then
      not_ready+=("$name")
    fi
  done

  ready=$(( ${#SERVICES[@]} - ${#not_ready[@]} ))
  echo "[${elapsed}s] Ready: ${ready}/${#SERVICES[@]}"

  if [[ ${#not_ready[@]} -eq 0 ]]; then
    echo "All services are healthy!"
    exit 0
  fi

  if [[ $elapsed -ge $MAX_WAIT ]]; then
    echo "Timeout after ${MAX_WAIT}s. Not ready: ${not_ready[*]}"
    exit 1
  fi

  sleep "$INTERVAL"
  elapsed=$(( elapsed + INTERVAL ))
done
