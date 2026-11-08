COMPOSE := docker compose -f infra/docker-compose.yaml
URL     := http://localhost:8080
S       ?= server-2

.PHONY: up up-gemini down clean chat send status logs kill start drain join test

## up: build and start NATS, MySQL, three servers and nginx on :8080
up:
	$(COMPOSE) up -d --build

## up-gemini: the same with Gemini CLI as the agent; needs GEMINI_API_KEY
up-gemini:
	FLEET_AGENT=gemini AGENT_COMMAND="gemini --experimental-acp" $(COMPOSE) up -d --build

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
	@$(COMPOSE) run --rm --no-deps -T server-1 status

## logs: follow the server logs
logs:
	$(COMPOSE) logs -f server-1 server-2 server-3 server-4

## kill: crash server S; start: start it again; drain: stop it gracefully
kill:
	$(COMPOSE) kill $(S)
start:
	$(COMPOSE) start $(S)
drain:
	$(COMPOSE) stop -t 90 $(S)

## join: add server-4 to the fleet
join:
	$(COMPOSE) --profile join up -d server-4

## test: run the integration tests (starts NATS and MySQL if needed)
test:
	go test -count=1 -timeout 5m ./...
