# ─────────────────────────────────────────────────────────────────────────────
# MEDBOT Platform – Makefile
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help build up down restart logs test test-health test-smoke \
        status pull-ollama-models clean reset infra-up infra-down \
        monitoring-up monitoring-down

COMPOSE     := docker compose
TIMEOUT     := 5
BASE_URL    := http://localhost

# Default target
help:
	@echo ""
	@echo "  MEDBOT Platform – Available Commands"
	@echo "  ──────────────────────────────────────────────────────────────"
	@echo "  make build           Build all 59 service images"
	@echo "  make up              Start full platform (infra + all services)"
	@echo "  make infra-up        Start only infrastructure (MongoDB/PG/Redis/Ollama)"
	@echo "  make down            Stop all containers"
	@echo "  make infra-down      Stop only infrastructure containers"
	@echo "  make restart         Restart all containers"
	@echo "  make status          Show container status"
	@echo "  make logs s=<name>   Stream logs for a specific service"
	@echo "  make logs-all        Stream logs for all services"
	@echo "  make test            Wait for services, then run full test suite"
	@echo "  make test-health     Run health checks only (no smoke tests)"
	@echo "  make test-smoke      Run full smoke test suite"
	@echo "  make pull-models     Pull required Ollama models"
	@echo "  make monitoring-up   Start Prometheus + Grafana + Nginx (monitoring stack)"
	@echo "  make monitoring-down Stop the monitoring stack"
	@echo "  make clean           Remove stopped containers and dangling images"
	@echo "  make reset           Stop, remove volumes, and rebuild everything"
	@echo ""
	@echo "  Grafana  : http://localhost:3000  (admin / medbot-admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  API      : http://localhost/api/  (via Nginx)"
	@echo ""

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	@echo "→ Building all service images..."
	$(COMPOSE) build --parallel

# ── Start / Stop ──────────────────────────────────────────────────────────────
infra-up:
	@echo "→ Starting infrastructure services..."
	$(COMPOSE) up -d mongodb postgresql redis ollama

infra-down:
	@echo "→ Stopping infrastructure services..."
	$(COMPOSE) stop mongodb postgresql redis ollama

up:
	@echo "→ Starting full MEDBOT platform..."
	$(COMPOSE) up -d
	@echo ""
	@echo "  Platform starting. Run 'make status' to see container health."
	@echo "  API Gateway: http://localhost:8000"
	@echo "  Run 'make test' once all services are up."

down:
	@echo "→ Stopping all containers..."
	$(COMPOSE) down

restart:
	@echo "→ Restarting all containers..."
	$(COMPOSE) restart

# ── Logs ──────────────────────────────────────────────────────────────────────
logs:
	$(COMPOSE) logs -f $(s)

logs-all:
	$(COMPOSE) logs -f

# ── Status ────────────────────────────────────────────────────────────────────
status:
	$(COMPOSE) ps

# ── Testing ───────────────────────────────────────────────────────────────────
test: _wait test-smoke

_wait:
	@echo "→ Waiting for services to be ready..."
	@bash scripts/wait_for_services.sh 180

test-health:
	@echo "→ Running health checks..."
	@TIMEOUT=$(TIMEOUT) BASE_URL=$(BASE_URL) bash scripts/test_services.sh

test-smoke:
	@echo "→ Running full smoke test suite..."
	@TIMEOUT=$(TIMEOUT) BASE_URL=$(BASE_URL) bash scripts/test_services.sh

# ── Ollama models ─────────────────────────────────────────────────────────────
pull-models:
	@echo "→ Pulling required Ollama models (this may take a while)..."
	docker exec $$($(COMPOSE) ps -q ollama) ollama pull llama3.2:latest
	docker exec $$($(COMPOSE) ps -q ollama) ollama pull llava:latest
	docker exec $$($(COMPOSE) ps -q ollama) ollama pull nomic-embed-text:latest
	docker exec $$($(COMPOSE) ps -q ollama) ollama pull phi3:mini
	@echo "→ All models pulled."

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	@echo "→ Removing stopped containers and dangling images..."
	$(COMPOSE) down --remove-orphans
	docker image prune -f

reset:
	@echo "→ Full reset: stopping, removing volumes, rebuilding..."
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) build --parallel
	$(COMPOSE) up -d
	@echo "→ Reset complete. Run 'make test' once services are ready."

# ── Monitoring stack ──────────────────────────────────────────────────────────
monitoring-up:
	@echo "→ Starting monitoring stack (Prometheus + Grafana + Nginx)..."
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana nginx
	@echo "  Grafana  : http://localhost:3000  (admin / medbot-admin)"
	@echo "  Prometheus: http://localhost:9090"

monitoring-down:
	@echo "→ Stopping monitoring stack..."
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml stop prometheus grafana nginx

# ── Individual service shortcuts ──────────────────────────────────────────────
.PHONY: gateway auth session triage rag

gateway:
	$(COMPOSE) up -d api_gateway

auth:
	$(COMPOSE) up -d auth_service

session:
	$(COMPOSE) up -d session_service

triage:
	$(COMPOSE) up -d triage_agent

rag:
	$(COMPOSE) up -d rag_agent_service
