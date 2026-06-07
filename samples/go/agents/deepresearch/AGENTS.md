# AGENTS.md — Deep Research Agent Style Guide

## Project Overview

This is a **multi-agent deep research system** built on the A2A (Agent-to-Agent) protocol. A single Go binary serves four agent roles — orchestrator, researcher, analyzer, synthesizer — selected at runtime via the `NODE_TYPE` environment variable. The system uses NATS JetStream for event sourcing and work distribution, MySQL for task persistence, and Gemini (via Google ADK) for LLM reasoning.

### Key dependencies

| Dependency | Purpose |
|---|---|
| `github.com/a2aproject/a2a-go/v2` | A2A protocol SDK (server, client, types, push, queues, stores) |
| `google.golang.org/adk` | Google Agent Development Kit (LLM agents, runners, sessions, tools) |
| `google.golang.org/genai` | Google GenAI SDK (Gemini model, content types) |
| `github.com/nats-io/nats.go` | NATS client / JetStream |
| `github.com/go-sql-driver/mysql` | MySQL driver (blank-imported for side effects) |

---

## Architecture

```
Client → Orchestrator (state machine)
           ├── Researcher  (Google Search grounding)
           ├── Analyzer    (referenced-task injection)
           └── Synthesizer (referenced-task injection)

Infrastructure: MySQL (task index + outbox) · NATS JetStream (events, work, state) · nginx (host-based LB)
```

- **Single binary, multi-role**: `main.go` reads `NODE_TYPE` and wires the corresponding `a2asrv.AgentExecutor`.
- **Event sourcing**: Tasks are materialized by replaying events from NATS streams.
- **Transactional outbox**: MySQL insert + NATS publish are guaranteed atomic via an outbox table relayed by a leader-elected poller.
- **Scatter/gather**: The orchestrator fans out subtasks via async A2A sends and gathers results through NATS push notifications.

---

## Project Layout

```
deepresearch/
├── main.go                         # Entry point, config, server wiring
├── internal/
│   ├── agents/                     # Agent executors (orchestrator, researcher, analyzer, synthesizer)
│   ├── clusterclient/              # Async A2A client wrapper for inter-agent communication
│   ├── domain/                     # Shared domain types (AgentType enum, Info)
│   ├── lease/                      # NATS KV-based leader election
│   ├── msgstream/                  # NATS-backed event queues, work queues, push sender
│   ├── report/                     # HTTP handler for serving synthesized reports
│   ├── server/                     # Server wiring (infra setup, handler creation)
│   ├── statemachine/               # Generic event-sourced state machine
│   ├── store/                      # MySQL-backed task store, indexing, transactional outbox
│   ├── testutil/                   # Shared test helpers
│   └── utils/                      # Small generic helpers (Must, SchemaFor)
├── infra/                          # Docker Compose, nginx, MySQL schema, NATS bootstrap
├── Dockerfile
└── go.mod
```

**Rules**:
- All domain logic lives under `internal/` — one concern per package.
- Each package should have a single clear responsibility (e.g., `lease` only does leader election).
- `main.go` is the only file in package `main`; it handles configuration, dependency wiring, and graceful shutdown.

---

## Coding Rules

## Testing

- Test observable behavior, not the internal state.
- Use table-driven tests where applicable.
- Name test functions `TestFunctionName_scenario`.

## Comments

- **Prefer self-explanatory code**.
- **Doc comments**: `// SymbolName does X.` directly above the symbol. Start with the symbol name per Go convention. Add for all exported symbols, but be brief.
- **Inline comments**: Use sparingly, be brief, explain *why* not *what*.
- **References**: Use Go doc-link syntax `[a2a.Client]` when referencing other symbols.

## Logging

Use `github.com/a2aproject/a2a-go/v2/log` exclusively. Do not use `log/slog` or `fmt.Println` for application logging.

---

## Things to Know

### Event-sourced state machine (`internal/statemachine/`)

The generic `statemachine.Spec[E, S]` (driven by `statemachine.Run`) drives the orchestrator:
- **Decode**: Parse raw NATS messages into typed events.
- **Evolve**: Apply events to state (pure state transitions, no side effects).
- **Act**: Inspect state and decide on side effects (dispatch subtasks, call LLM, complete).

### Transactional outbox (`internal/store/outbox.go`)

Guarantees atomicity between MySQL writes and NATS publishes:
1. Insert task + outbox row (tagged with the agent type) in the same SQL transaction.
2. A leader-elected poller reads outbox rows for its own agent type, publishes to NATS, then deletes.

### Decorator pattern (`internal/agents/common.go`)

`referencedTaskLoader` wraps an `AgentExecutor` via embedding and intercepts `Execute` to inject referenced task content before delegating to the inner executor.

### Leader election (`internal/lease/`)

Uses NATS KV `Create` (atomic put-if-absent) for distributed locking. Watches for key deletion to retry acquisition.

### Infrastructure

All services are defined in `infra/docker-compose.yaml`.

### Misc

- This agent is a **self-contained Go module** (`go.mod` at the deepresearch root). It does not share code with other Go samples in the repository.
- The A2A SDK (`a2a-go/v2`) provides the server framework, client, types, and infrastructure interfaces (queues, stores, push). Domain logic implements these interfaces.
- The orchestrator's workflow proceeds through stages: **research -> analyze -> follow-up research -> synthesize -> complete**.
