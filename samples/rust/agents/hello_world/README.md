# Hello World Agent (Rust) 🦀

A simple Agent2Agent (A2A) protocol agent written in Rust that responds with greetings.

## Overview

This agent demonstrates the basic structure of an A2A agent using the Rust A2A framework. It responds to messages with either a standard "Hello World" or a more enthusiastic "SUPER HELLO WORLD!" depending on the input.

## Features

- **Two greeting modes**:
  - Standard: Returns "Hello World"
  - Super: Returns "🌟 SUPER HELLO WORLD! 🌟" (triggered by messages containing "super")
- **Built with**: `a2a-core` and `a2a-server` Rust libraries
- **Async runtime**: Powered by Tokio
- **HTTP server**: Built on Axum

## Prerequisites

- Rust 1.75 or later
- Cargo (comes with Rust)

## Installation

### 1. Clone the repository:

```bash
git clone https://github.com/google-a2a/a2a-samples.git
cd a2a-samples/samples/rust/agents/hello_world
```

### 2. Build the agent:

```bash
cargo build
```

### 3. Run the agent:

```bash
cargo run
```

The agent will start on `http://localhost:9999`.

## Usage

### Get Agent Card

Retrieve the agent's metadata:

```bash
curl http://localhost:9999/agent-card
```

Response:
```json
{
  "name": "Hello World Agent (Rust)",
  "description": "A simple hello world agent written in Rust 🦀",
  "url": "http://localhost:9999",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    {
      "id": "hello_world",
      "name": "Returns hello world",
      "description": "Just returns hello world",
      "tags": ["hello world", "greeting"],
      "examples": ["hi", "hello world", "say hello"]
    },
    {
      "id": "super_hello_world",
      "name": "Returns a SUPER Hello World",
      "description": "A more enthusiastic greeting with sparkles ✨",
      "tags": ["hello world", "super", "greeting"],
      "examples": ["super hi", "give me a super hello", "super hello world"]
    }
  ]
}
```

### Send a Message

#### Basic greeting:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "hello"
          }
        ]
      }
    }
  }'
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-001",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "name": "agent message",
        "parts": [
          {
            "type": "text",
            "text": "Hello World"
          }
        ],
        "lastChunk": true
      }
    ]
  }
}
```

#### Super greeting:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "id": "task-002",
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "super hi"
          }
        ]
      }
    }
  }'
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "id": "task-002",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "name": "agent message",
        "parts": [
          {
            "type": "text",
            "text": "🌟 SUPER HELLO WORLD! 🌟"
          }
        ],
        "lastChunk": true
      }
    ]
  }
}
```

### Get Task Status

Retrieve the status of a previously sent task:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "tasks/get",
    "params": {
      "id": "task-001"
    }
  }'
```

### Cancel a Task

Cancel an ongoing task:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "4",
    "method": "tasks/cancel",
    "params": {
      "id": "task-001"
    }
  }'
```

### Health Check

Check if the server is running:

```bash
curl http://localhost:9999/health
```

Response: `OK`

## Code Structure

```
hello_world/
├── Cargo.toml          # Package configuration
├── README.md           # This file
└── src/
    └── main.rs         # Main agent implementation
```

### Key Components

**HelloWorldAgent**: Implements the `AgentExecutor` trait with:
- `execute()`: Processes incoming messages and generates responses
- `cancel()`: Handles task cancellation (no-op for this simple agent)

**Agent Card**: Defines the agent's metadata, capabilities, and skills

**Server Setup**: Configures the HTTP server with Axum on port 9999

## Configuration

### Change Port

Edit `main.rs` and modify:

```rust
let server = A2AServer::new(agent_card, executor, task_store)
    .with_port(8080);  // Change to your desired port
```

### Change Host

```rust
let server = A2AServer::new(agent_card, executor, task_store)
    .with_host("127.0.0.1")  // Change to your desired host
    .with_port(9999);
```

### Logging

Set the `RUST_LOG` environment variable:

```bash
RUST_LOG=debug cargo run
```

Levels: `error`, `warn`, `info`, `debug`, `trace`

## Development

### Run with logs:

```bash
RUST_LOG=info cargo run
```

### Build optimized binary:

```bash
cargo build --release
```

Binary location: `target/release/hello_world_agent`

### Format code:

```bash
cargo fmt
```

### Run linter:

```bash
cargo clippy
```

## Using as a Template

This agent serves as a simple template for building your own A2A agents. Key patterns to follow:

1. **Implement AgentExecutor**: Define your agent logic in the `execute()` method
2. **Use EventQueue**: Send messages and status updates via the event queue
3. **Define AgentCard**: Describe your agent's capabilities and skills
4. **Create Server**: Initialize and run the `A2AServer`

See the main [Rust README](../../README.md) for more advanced examples.

## Troubleshooting

### Port already in use

If port 9999 is already in use, either:
1. Stop the other process using the port
2. Change the port in `main.rs` (see Configuration section)

### Build errors

Ensure you have the latest Rust toolchain:

```bash
rustup update
```

### Connection refused

Make sure the agent is running and listening on the correct host/port:

```bash
curl http://localhost:9999/health
```

## Related Resources

- [Rust A2A Framework Documentation](../../README.md)
- [A2A Protocol Specification](https://github.com/google-a2a/a2a)
- [More A2A Samples](https://github.com/google-a2a/a2a-samples)

## License

MIT OR Apache-2.0
