COMPOSE     := docker compose --env-file .env -f infra/docker-compose.yaml
NATS_URL    := nats://localhost:4222
MYSQL_DSN   := root:root@tcp(localhost:3306)/planner?parseTime=true

# Local ports (go run mode)
ORCH_PORT   := 8080
RESEARCH_PORT := 8081
ANALYZE_PORT  := 8082
SYNTH_PORT    := 8083

# ── Docker Compose ──────────────────────────────────────────────

.PHONY: up force-up infra-up down clean

## up: start all services (cached images)
up:
	$(COMPOSE) up -d

## force-up: rebuild images and start all services
force-up:
	$(COMPOSE) up --build -d

## infra-up: start only NATS, MySQL, and run the NATS init script
infra-up:
	$(COMPOSE) up nats mysql -d
	$(COMPOSE) run --rm nats-init

## down: stop all services (preserves volumes)
down:
	$(COMPOSE) down

## clean: stop all services and remove volumes
clean:
	$(COMPOSE) down -v

# ── Local Mode (go run) ────────────────────────────────────────
# Runs all four agents as local processes against containerised
# NATS + MySQL. No nginx needed — the orchestrator connects to
# researcher/analyzer/synthesizer directly on localhost ports.
#
# Prerequisites: make infra-up
# Usage:         make local
# Stop:          Ctrl-C (kills all four processes)

.PHONY: local

local:
	@if [ -z "$$GOOGLE_API_KEY" ] && [ -f infra/.env ]; then \
		export $$(grep -v '^#' infra/.env | xargs); \
	fi; \
	trap 'kill 0' EXIT; \
	GOOGLE_API_KEY=$${GOOGLE_API_KEY} NODE_TYPE=researcher  LISTEN_ADDR=:$(RESEARCH_PORT) go run . & \
	GOOGLE_API_KEY=$${GOOGLE_API_KEY} NODE_TYPE=analyzer    LISTEN_ADDR=:$(ANALYZE_PORT)  go run . & \
	GOOGLE_API_KEY=$${GOOGLE_API_KEY} NODE_TYPE=synthesizer LISTEN_ADDR=:$(SYNTH_PORT)    go run . & \
	sleep 1; \
	GOOGLE_API_KEY=$${GOOGLE_API_KEY} \
	REPORT_URL=http://127.0.0.1:8080 \
	NODE_TYPE=orchestrator \
	LISTEN_ADDR=:$(ORCH_PORT) \
	RESEARCHER_URL=http://localhost:$(RESEARCH_PORT) \
	ANALYZER_URL=http://localhost:$(ANALYZE_PORT) \
	SYNTHESIZER_URL=http://localhost:$(SYNTH_PORT) \
	go run . ; \
	wait

# ── Testing ─────────────────────────────────────────────────────

.PHONY: test send

## test: run integration tests (starts infra containers automatically)
test:
	go test -v -timeout 60s ./itest/

## send: send a test message to the orchestrator via the a2a CLI
send:
	a2a send http://localhost:$(ORCH_PORT) "Research the impact of AI on healthcare"  --transport rest --stream --timeout 5m
