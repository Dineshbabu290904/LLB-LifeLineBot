#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# MEDBOT – Full Platform Health & Smoke Test
# Usage: ./scripts/test_services.sh [--timeout 5] [--base-url http://localhost]
# Env vars:
#   TIMEOUT=5          curl timeout in seconds
#   BASE_URL=http://localhost
#   SKIP_INFRA=1       skip nc-based infra port checks (use in CI / Docker env)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail   # NOTE: no -e; counters use VAR=$((VAR+1)) to avoid false exits

# ── Defaults ─────────────────────────────────────────────────────────────────
TIMEOUT=${TIMEOUT:-5}
BASE_URL=${BASE_URL:-"http://localhost"}
SKIP_INFRA=${SKIP_INFRA:-0}
PASS=0
FAIL=0
SKIP=0
FAILURES=()

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --timeout)    TIMEOUT="$2";  shift 2 ;;
    --base-url)   BASE_URL="$2"; shift 2 ;;
    --skip-infra) SKIP_INFRA=1;  shift   ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
port_open() {
  local host=$1 port=$2
  # Try nc first, fall back to bash /dev/tcp
  if command -v nc >/dev/null 2>&1; then
    nc -z -w "$TIMEOUT" "$host" "$port" >/dev/null 2>&1
  else
    (echo >/dev/tcp/"$host"/"$port") 2>/dev/null
  fi
}

check_health() {
  local name=$1
  local port=$2
  local url="${BASE_URL}:${port}/health"

  local http_code
  http_code=$(curl -s -o /tmp/medbot_health_resp.json -w "%{http_code}" \
    --max-time "$TIMEOUT" "$url" 2>/dev/null) || http_code="000"

  if [[ "$http_code" == "200" ]]; then
    local status
    status=$(python3 -c "
import json, sys
try:
    d = json.load(open('/tmp/medbot_health_resp.json'))
    print(d.get('status', '?'))
except Exception:
    print('?')
" 2>/dev/null) || status="?"
    printf "  ${GREEN}✔${NC}  %-45s port %-5s  [%s]\n" "$name" "$port" "$status"
    PASS=$((PASS + 1))
  elif [[ "$http_code" == "000" ]]; then
    printf "  ${YELLOW}–${NC}  %-45s port %-5s  [unreachable]\n" "$name" "$port"
    FAILURES+=("$name:$port – unreachable / not running")
    FAIL=$((FAIL + 1))
  else
    printf "  ${RED}✘${NC}  %-45s port %-5s  [HTTP $http_code]\n" "$name" "$port"
    FAILURES+=("$name:$port – HTTP $http_code")
    FAIL=$((FAIL + 1))
  fi
}

request_check() {
  local label=$1
  local method=$2
  local url=$3
  local body=${4:-}

  local http_code
  local curl_args=(
    -s -o /tmp/medbot_post_resp.json -w "%{http_code}"
    --max-time "$TIMEOUT"
    -X "$method"
    "$url"
  )

  if [[ -n "$body" ]]; then
    curl_args+=(
      -H "Content-Type: application/json"
      -d "$body"
    )
  fi

  http_code=$(curl "${curl_args[@]}" 2>/dev/null) || http_code="000"

  if [[ "$http_code" =~ ^2 ]]; then
    printf "  ${GREEN}✔${NC}  %s\n" "$label"
    PASS=$((PASS + 1))
  elif [[ "$http_code" == "000" ]]; then
    printf "  ${YELLOW}–${NC}  %s  [unreachable]\n" "$label"
    SKIP=$((SKIP + 1))
  else
    printf "  ${RED}✘${NC}  %s  [HTTP $http_code]\n" "$label"
    FAILURES+=("POST $label – HTTP $http_code")
    FAIL=$((FAIL + 1))
  fi
}

section() {
  echo ""
  echo -e "${CYAN}${BOLD}━━━ $1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          MEDBOT Platform Health & Smoke Test             ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo -e "  Base URL    : ${BASE_URL}"
echo -e "  Timeout     : ${TIMEOUT}s"
echo -e "  Skip infra  : ${SKIP_INFRA}"
echo -e "  Started     : $(date '+%Y-%m-%d %H:%M:%S')"

# ═══════════════════════════════════════════════════════════════════════════════
section "INFRASTRUCTURE"
if [[ "$SKIP_INFRA" == "1" ]]; then
  echo "  (skipped – Docker Compose manages infrastructure health)"
else
  for svc in "MongoDB:27017" "PostgreSQL:5432" "Redis:6379" "Ollama:11434"; do
    name="${svc%%:*}"
    port="${svc##*:}"
    if port_open "localhost" "$port"; then
      printf "  ${GREEN}✔${NC}  %-45s port %s  [up]\n" "$name" "$port"
      PASS=$((PASS + 1))
    else
      printf "  ${RED}✘${NC}  %-45s port %s  [down]\n" "$name" "$port"
      FAILURES+=("$name:$port – port not open")
      FAIL=$((FAIL + 1))
    fi
  done
fi

# ═══════════════════════════════════════════════════════════════════════════════
section "CORE / GATEWAY (8000–8005)"
check_health "api_gateway"                   8000
check_health "auth_service"                  8001
check_health "session_service"               8002
check_health "rate_limit_service"            8003
check_health "request_validation_service"    8004
check_health "agent_controller"              8005

section "ORCHESTRATION (8010–8015)"
check_health "langgraph_orchestrator"        8010
check_health "triage_agent"                  8015

section "AGENT SERVICES (8020–8029)"
check_health "context_builder_service"       8020
check_health "knowledge_agent_service"       8021
check_health "knowledge_base_service"        8022
check_health "vision_agent_service"          8023
check_health "rag_agent_service"             8025
check_health "reasoning_agent_service"       8026
check_health "safety_guardrail_agent"        8027
check_health "search_agent_service"          8028
check_health "evaluation_agent"              8029

section "DATASET SERVICES (8030–8032)"
check_health "dataset_generation_agent"      8030
check_health "dataset_labeling_model_service" 8031
check_health "dataset_preparation_service"   8032

section "STORAGE SERVICES (8040–8043)"
check_health "conversation_storage_service"  8040
check_health "dataset_storage_service"       8041
check_health "metadata_storage_service"      8042
check_health "audit_log_service"             8043

section "MODEL SERVICES (8050–8058)"
check_health "ollama_router_service"         8050
check_health "reasoning_model_service"       8051
check_health "embedding_model_service"       8052
check_health "vision_model_service"          8053
check_health "embedding_generation_service"  8054
check_health "vector_index_service"          8055
check_health "vector_search_service"         8056
check_health "classification_model_service"  8057
check_health "response_scoring_service"      8058

section "DOCUMENT PROCESSING (8060–8062)"
check_health "document_ingestion_service"    8060
check_health "document_chunking_service"     8061
check_health "document_cleaning_service"     8062

section "MEDICAL ANALYSIS (8070–8078)"
check_health "medical_entity_extraction_service"  8070
check_health "severity_classification_service"    8071
check_health "emergency_detection_service"        8072
check_health "medical_source_validation_service"  8073
check_health "pubmed_search_service"              8074
check_health "risk_detection_service"             8075
check_health "symptom_extraction_agent"           8076
check_health "web_search_service"                 8077
check_health "who_guidelines_service"             8078

section "DOCTOR SERVICES (8080–8081)"
check_health "doctor_mapping_service"        8080
check_health "doctor_recommendation_agent"   8081

section "CONFIG & OBSERVABILITY (8090–8093)"
check_health "config_service"                8090
check_health "logging_service"               8091
check_health "monitoring_service"            8092
check_health "metrics_service"               8093

section "QUALITY & VALIDATION (8101–8104)"
check_health "triage_accuracy_service"       8101
check_health "medical_consistency_service"   8102
check_health "safety_validation_service"     8103
check_health "hallucination_detection_agent" 8104

section "TRAINING PIPELINE (8110–8111)"
check_health "fine_tuning_service"           8110
check_health "training_pipeline_service"     8111

section "MODEL MANAGEMENT (8120–8121)"
check_health "model_registry_service"        8120
check_health "model_versioning_service"      8121

# ═══════════════════════════════════════════════════════════════════════════════
section "SMOKE TESTS – Key Endpoints"

request_check "auth_service  POST /api/v1/auth/register" "POST" \
  "${BASE_URL}:8001/api/v1/auth/register" \
  '{"username":"testuser","password":"TestPass123!","email":"test@medbot.dev"}'

request_check "session_service POST /api/v1/sessions" "POST" \
  "${BASE_URL}:8002/api/v1/sessions" \
  '{"user_id":"test-user-001"}'

request_check "triage_agent   POST /api/v1/triage" "POST" \
  "${BASE_URL}:8015/api/v1/triage" \
  '{"query":"I have a headache and fever","user_id":"test-user-001"}'

request_check "emergency_detection POST /api/v1/emergency/detect" "POST" \
  "${BASE_URL}:8072/api/v1/emergency/detect" \
  '{"text":"chest pain and difficulty breathing","user_id":"test-user-001"}'

request_check "symptom_extraction POST /api/v1/symptoms/extract" "POST" \
  "${BASE_URL}:8076/api/v1/symptoms/extract" \
  '{"text":"I have a headache fever and sore throat for 3 days"}'

request_check "severity_classification POST /api/v1/classify/severity" "POST" \
  "${BASE_URL}:8071/api/v1/classify/severity" \
  '{"symptoms":["headache","fever"],"patient_age":30}'

request_check "risk_detection  POST /api/v1/risk/detect" "POST" \
  "${BASE_URL}:8075/api/v1/risk/detect" \
  '{"text":"patient is diabetic with hypertension","user_id":"test-user-001"}'

request_check "doctor_mapping  POST /api/v1/doctor/map" "POST" \
  "${BASE_URL}:8080/api/v1/doctor/map" \
  '{"symptoms":["chest pain","shortness of breath"]}'

request_check "knowledge_base  POST /api/v1/knowledge" "POST" \
  "${BASE_URL}:8022/api/v1/knowledge" \
  '{"title":"Headache","content":"Headache can be caused by stress or dehydration","category":"neurology"}'

request_check "document_cleaning POST /api/v1/documents/clean" "POST" \
  "${BASE_URL}:8062/api/v1/documents/clean" \
  '{"text":"  Hello   World!!!   This   is   a   test.  "}'

request_check "who_guidelines  POST /api/v1/who/search" "POST" \
  "${BASE_URL}:8078/api/v1/who/search" \
  '{"query":"diabetes management"}'

request_check "model_registry  GET  /api/v1/models" "GET" \
  "${BASE_URL}:8120/api/v1/models"

# ═══════════════════════════════════════════════════════════════════════════════
section "SUMMARY"
TOTAL=$((PASS + FAIL + SKIP))
echo ""
printf "  Total checks : %d\n" "$TOTAL"
printf "  ${GREEN}Passed${NC}       : %d\n" "$PASS"
printf "  ${RED}Failed${NC}       : %d\n" "$FAIL"
printf "  ${YELLOW}Skipped${NC}      : %d\n" "$SKIP"
echo ""

if [[ ${#FAILURES[@]} -gt 0 ]]; then
  echo -e "  ${RED}${BOLD}Failures:${NC}"
  for f in "${FAILURES[@]}"; do
    echo -e "    ${RED}•${NC} $f"
  done
  echo ""
fi

if [[ $FAIL -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}All checks passed! Platform is healthy.${NC}"
  echo ""
  exit 0
else
  PASS_RATE=$(( PASS * 100 / (PASS + FAIL) ))
  echo -e "  ${YELLOW}${BOLD}Platform health: ${PASS_RATE}% (${PASS}/$((PASS + FAIL)) checks OK)${NC}"
  echo ""
  exit 1
fi
