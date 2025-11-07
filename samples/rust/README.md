# Rust A2A Samples 🦀

This directory contains Rust implementations of the Agent2Agent (A2A) Protocol, including a comprehensive framework for building A2A agents and example implementations.

## Overview

The Rust A2A implementation provides:

- **a2a-core**: Core protocol types and structures (AgentCard, Task, Message, JSON-RPC, etc.)
- **a2a-server**: HTTP server framework built on Axum for creating A2A agents
- **agents/**: Example agent implementations

## Architecture

```
rust/
├── a2a-core/           # Core protocol types library
├── a2a-server/         # HTTP server framework
└── agents/
    └── hello_world/    # Example Hello World agent
```

### Key Components

#### a2a-core

Core types for the A2A protocol:

- **Types**: `AgentCard`, `Task`, `Message`, `Artifact`, `Part`, `TaskState`, etc.
- **JSON-RPC**: Request/response structures and error handling
- **Serialization**: Full serde support for JSON serialization

#### a2a-server

Server framework for building A2A agents:

- **AgentExecutor**: Trait-based abstraction for implementing agent logic
- **A2AServer**: HTTP server built on Axum with built-in JSON-RPC handling
- **TaskStore**: Trait for task persistence with in-memory implementation
- **EventQueue**: Async event system for agent communication

## Prerequisites

- **Rust**: 1.75 or later
- **Cargo**: Rust's package manager (comes with Rust)

Install Rust from [rustup.rs](https://rustup.rs/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

## Getting Started

### Running the Hello World Agent

```bash
cd agents/hello_world
cargo run
```

The agent will start on `http://localhost:9999`.

### Testing the Agent

Get the agent card:

```bash
curl http://localhost:9999/agent-card
```

Send a message:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "id": "task-123",
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

Get task status:

```bash
curl -X POST http://localhost:9999/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tasks/get",
    "params": {
      "id": "task-123"
    }
  }'
```

## Creating Your Own Agent

### 1. Add to Workspace

Create a new directory in `agents/`:

```bash
mkdir -p agents/my_agent/src
```

Create `agents/my_agent/Cargo.toml`:

```toml
[package]
name = "my_agent"
version.workspace = true
edition.workspace = true

[[bin]]
name = "my_agent"
path = "src/main.rs"

[dependencies]
a2a-core = { workspace = true }
a2a-server = { workspace = true }
tokio = { workspace = true }
async-trait = { workspace = true }
anyhow = { workspace = true }
tracing = { workspace = true }
tracing-subscriber = { workspace = true }
```

Update the root `Cargo.toml` to include your agent:

```toml
[workspace]
members = [
    "a2a-core",
    "a2a-server",
    "agents/hello_world",
    "agents/my_agent",  # Add this line
]
```

### 2. Implement AgentExecutor

Create `agents/my_agent/src/main.rs`:

```rust
use a2a_core::types::{AgentCard, AgentCapabilities, AgentSkill, Message, Task};
use a2a_server::{
    executor::{AgentExecutor, EventQueue, RequestContext},
    store::InMemoryTaskStore,
    A2AServer,
};
use async_trait::async_trait;
use std::sync::Arc;

struct MyAgent;

#[async_trait]
impl AgentExecutor for MyAgent {
    async fn execute(
        &self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> anyhow::Result<()> {
        // Your agent logic here
        tracing::info!("Processing task: {}", context.task_id);

        // Extract user message
        let user_text = context
            .message
            .parts
            .iter()
            .find_map(|part| part.text.as_ref())
            .unwrap_or(&"".to_string());

        // Process and generate response
        let response_text = format!("You said: {}", user_text);
        let response = Message::agent_text(response_text);

        // Send response
        event_queue.send_message(response).await?;

        // Complete task
        let task = Task::new(context.task_id).complete();
        event_queue.send_completed(task).await?;

        Ok(())
    }

    async fn cancel(&self, _context: RequestContext) -> anyhow::Result<()> {
        Ok(())
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let agent_card = AgentCard {
        name: "My Agent".to_string(),
        description: Some("My custom A2A agent".to_string()),
        url: "http://localhost:9999".to_string(),
        version: "1.0.0".to_string(),
        capabilities: AgentCapabilities::default(),
        authentication: None,
        provider: None,
        documentation_url: None,
        default_input_modes: Some(vec!["text".to_string()]),
        default_output_modes: Some(vec!["text".to_string()]),
        skills: vec![
            AgentSkill {
                id: "echo".to_string(),
                name: "Echo messages".to_string(),
                description: Some("Echoes back your message".to_string()),
                tags: None,
                examples: Some(vec!["hello".to_string()]),
                input_modes: None,
                output_modes: None,
            }
        ],
    };

    let server = A2AServer::new(
        agent_card,
        Arc::new(MyAgent),
        Arc::new(InMemoryTaskStore::new()),
    )
    .with_port(9999);

    server.run().await
}
```

### 3. Run Your Agent

```bash
cd agents/my_agent
cargo run
```

## Advanced Features

### Adding External APIs (e.g., Grok SDK)

To integrate external APIs like the Grok SDK:

```toml
# Add to your agent's Cargo.toml
[dependencies]
reqwest = { version = "0.11", features = ["json"] }
```

```rust
use reqwest::Client;

struct GrokAgent {
    client: Client,
    api_key: String,
}

#[async_trait]
impl AgentExecutor for GrokAgent {
    async fn execute(
        &self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> anyhow::Result<()> {
        // Call Grok API
        let response = self.client
            .post("https://api.grok.com/v1/chat")
            .bearer_auth(&self.api_key)
            .json(&serde_json::json!({
                "message": context.message
            }))
            .send()
            .await?;

        // Process response and send via event queue
        let grok_response = response.json::<YourResponseType>().await?;
        event_queue.send_message(Message::agent_text(grok_response.text)).await?;

        let task = Task::new(context.task_id).complete();
        event_queue.send_completed(task).await?;

        Ok(())
    }

    async fn cancel(&self, _context: RequestContext) -> anyhow::Result<()> {
        Ok(())
    }
}
```

### Streaming Support

For streaming responses, send multiple messages via the event queue:

```rust
async fn execute(
    &self,
    context: RequestContext,
    event_queue: EventQueue,
) -> anyhow::Result<()> {
    // Send chunks as they arrive
    for chunk in stream {
        let msg = Message::agent_text(chunk);
        event_queue.send_message(msg).await?;
    }

    // Mark complete when done
    let task = Task::new(context.task_id).complete();
    event_queue.send_completed(task).await?;

    Ok(())
}
```

### Custom Task Storage

Implement the `TaskStore` trait for persistent storage:

```rust
use a2a_server::store::TaskStore;
use async_trait::async_trait;

struct DatabaseTaskStore {
    // Your database connection
}

#[async_trait]
impl TaskStore for DatabaseTaskStore {
    async fn store_task(&self, task: Task) -> anyhow::Result<()> {
        // Store in database
        Ok(())
    }

    async fn get_task(&self, id: &str) -> anyhow::Result<Option<Task>> {
        // Retrieve from database
        Ok(None)
    }

    // Implement other methods...
}
```

## Building for Production

### Build optimized binary:

```bash
cargo build --release
```

Binary will be in `target/release/`.

### Using Docker

Create a `Dockerfile` in your agent directory:

```dockerfile
FROM rust:1.75 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/my_agent /usr/local/bin/
CMD ["my_agent"]
```

Build and run:

```bash
docker build -t my-a2a-agent .
docker run -p 9999:9999 my-a2a-agent
```

## Development

### Running tests:

```bash
cargo test
```

### Checking code:

```bash
cargo check
cargo clippy
cargo fmt
```

### Building documentation:

```bash
cargo doc --open
```

## API Reference

### Core Types

- **AgentCard**: Metadata describing the agent
- **Task**: Represents a task being processed
- **Message**: A message in the conversation
- **Part**: A part of a message (text, file, data)
- **Artifact**: Output from a task

### Server Components

- **AgentExecutor**: Main trait for implementing agent logic
- **EventQueue**: Send events during execution
- **TaskStore**: Store and retrieve tasks
- **A2AServer**: HTTP server for the agent

### JSON-RPC Methods

Supported methods:
- `message/send`: Send a message to the agent
- `tasks/get`: Get task status
- `tasks/cancel`: Cancel a task

## Examples

See the `agents/` directory for complete examples:

- **hello_world**: Simple greeting agent

## Resources

- [A2A Protocol Specification](https://github.com/google-a2a/a2a)
- [A2A Samples Repository](https://github.com/google-a2a/a2a-samples)
- [Rust Documentation](https://doc.rust-lang.org/)
- [Axum Documentation](https://docs.rs/axum/)
- [Tokio Documentation](https://tokio.rs/)

## Contributing

Contributions are welcome! Please follow the standard Rust coding conventions and ensure all tests pass.

## License

MIT OR Apache-2.0
