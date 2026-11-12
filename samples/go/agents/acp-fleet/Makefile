COMPOSE := docker compose -f infra/docker-compose.yaml
TOOLS   := $(COMPOSE) --progress quiet run --rm --no-deps
URL     := http://localhost:8080
S       ?= server-2

.PHONY: up up-opencode down clean chat send status watch crowd logs kill start drain join test

FLEET_MODEL ?= google/gemini-3-flash-preview

# infra/.env keeps the agent of the fleet for the commands that follow, such as join.

## up: build and start NATS, MySQL, three servers with the fake agent and nginx on :8080
up:
	@printf 'FLEET_AGENT=fake\n' > infra/.env
	$(COMPOSE) up -d --build

## up-opencode: the same with opencode on Gemini as the agent; needs GEMINI_API_KEY
up-opencode:
	@test -n "$$GEMINI_API_KEY" || { echo "set GEMINI_API_KEY" >&2; exit 1; }
	@printf 'FLEET_AGENT=opencode\nFLEET_MODEL=%s\n' "$(FLEET_MODEL)" > infra/.env
	$(COMPOSE) up -d --build

## down: stop everything; clean: also remove the data
down:
	$(COMPOSE) --profile join down
clean:
	$(COMPOSE) --profile join down -v

## chat: talk to the fleet with the a2a CLI (v0.4.0 or later)
chat:
	a2a chat --stream --timeout 10m -a $(URL)

## send: send MSG to the fleet
send:
	a2a send --stream --timeout 10m -a $(URL) "$(MSG)"

## status: show which server owns how many shards and conversations
status:
	@$(TOOLS) -T tools status

## watch: show the servers, shards and conversations live
watch:
	@$(TOOLS) tools watch

## crowd: simulate N users (default 6) and check what their agents remember
N ?= 6
crowd:
	@$(TOOLS) -T tools crowd $(N)

## logs: follow the server logs
logs:
	$(COMPOSE) logs -f server-1 server-2 server-3 server-4

## kill: crash server S; start: start it again; drain: stop it gracefully
kill:
	@$(COMPOSE) kill $(S)
start:
	@$(COMPOSE) start $(S)
drain:
	@$(COMPOSE) stop -t 90 $(S)

## join: add server-4 to the fleet
join:
	@$(COMPOSE) --progress quiet --profile join up -d server-4
	@echo "server-4 started"

## test: run the integration tests (starts NATS and MySQL if needed)
test:
	go test -count=1 -timeout 5m ./...
