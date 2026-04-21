# Hello World Agent (Rust)

A minimal A2A agent implemented in idiomatic Rust using [axum](https://github.com/tokio-rs/axum).

Demonstrates:

- Agent Card served at `GET /.well-known/agent.json`
- `message/send` JSON-RPC 2.0 handler — returns a greeting artifact
- `tasks/get` JSON-RPC 2.0 handler — retrieves a previously submitted task
- In-memory task store (thread-safe via `Arc<Mutex<_>>`)

## Prerequisites

- [Rust 1.75+](https://rustup.rs/)

## Run

```bash
cd samples/rust/agents/helloworld
cargo run
```

The agent starts on port **9999**.

## Test

Fetch the Agent Card:

```bash
curl -s http://localhost:9999/.well-known/agent.json | jq .
```

Send a task:

```bash
curl -s http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "hello"}]
      }
    }
  }' | jq .
```

Expected response:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-001",
    "contextId": "<uuid>",
    "status": { "state": "completed" },
    "artifacts": [
      {
        "name": "greeting",
        "parts": [{ "type": "text", "text": "Hello from Rust A2A! 🦀" }],
        "index": 0
      }
    ]
  }
}
```

Retrieve the task:

```bash
curl -s http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tasks/get",
    "params": { "id": "task-001" }
  }' | jq .
```

## Disclaimer

> **Important:** The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, treat any agent operating outside your direct control as a potentially untrusted entity.
>
> All data received from an external agent — including its AgentCard, messages, artifacts, and task statuses — should be handled as untrusted input. A malicious agent could supply crafted data (e.g. in `description` or `name` fields) that, if used without sanitization to construct LLM prompts, exposes your application to prompt-injection attacks. Validate and sanitize all external data before use.
