# Agent-to-Agent (A2A) with Koog Framework Examples

This project demonstrates how to build A2A-enabled agents using [Koog](https://github.com/JetBrains/koog), the official JetBrains' framework for building predictable,
fault-tolerant, and enterprise-ready AI agents, targeting JVM backend, Android, iOS, JS, and WasmJS.

## What is Koog?

Koog is JetBrains' open-source agentic framework that empowers developers to build AI agents using Kotlin. It provides:

- **Graph-based agent architecture**: Define agent behavior as a graph of nodes and edges with type-safe inputs and outputs,
  making complex workflows easier to understand and maintain
- **Multi-platform support**: Deploy agents across JVM, Android, native iOS, JS, and WasmJS using Kotlin Multiplatform
- **Fault tolerance**: Built-in retry mechanisms and agent state persistence for reliable execution, allowing to recover
  crashed agents even on another machine.
- **Prompt DSL**: Clean, type-safe DSL for building LLM prompts and automatically managing conversation context
- **Enterprise integrations**: Works seamlessly with Spring Boot, Ktor, and other JVM frameworks
- **Advanced Observability**: Built-in integrations with enterprise observability tools like Langfuse and W&B Weave via OpenTelemetry
- **A2A protocol support**: Built-in support for Agent-to-Agent communication via the A2A protocol

Learn more at [koog.ai](https://koog.ai/)

## Prerequisites

- JDK 17 or higher
- Set `GOOGLE_API_KEY` environment variable (or configure other LLM providers in the code)

## Examples

### Simple Joke Agent: [simplejoke](./src/main/kotlin/ai/koog/example/simplejoke)

A basic example demonstrating message-based A2A communication without task workflows.

**What it demonstrates:**
- Creating an `AgentExecutor` that wraps LLM calls using Koog's prompt DSL
- Setting up an A2A server with an `AgentCard` that describes agent capabilities
- Managing conversation context with message storage
- Simple request-response pattern using `sendMessage()`

**Run:**
```bash
# Terminal 1: Start server (port 9998)
./gradlew runExampleSimpleJokeServer

# Terminal 2: Run client
./gradlew runExampleSimpleJokeClient
```

### Advanced Joke Agent: [advancedjoke](./src/main/kotlin/ai/koog/example/advancedjoke)

A sophisticated example showcasing task-based A2A workflows using Koog's graph-based agent architecture.

**What it demonstrates:**
- **Graph-based agent design**: Uses Koog's `GraphAIAgent` with nodes and edges to create a maintainable workflow
- **Task lifecycle management**: Full A2A task states (Submitted → Working → InputRequired → Completed)
- **Interactive clarification**: Agent can request additional information using the InputRequired state
- **Structured LLM outputs**: Uses sealed interfaces with `nodeLLMRequestStructured` for type-safe agent decisions
- **Artifact delivery**: Returns final results as A2A artifacts
- **Streaming events**: Sends real-time task updates via `sendTaskEvent()`

**Run:**
```bash
# Terminal 1: Start server (port 9999)
./gradlew runExampleAdvancedJokeServer

# Terminal 2: Run client
./gradlew runExampleAdvancedJokeClient
```

## Key Patterns & Koog Concepts

### A2A Communication Patterns

**Simple Agent:** `sendMessage()` → single response
**Advanced Agent:** `sendMessageStreaming()` → Flow of events (Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent)

**Task States:** Submitted → Working → InputRequired (optional) → Completed

### Koog Framework Concepts Used

**AgentExecutor**: The entry point for A2A requests. Receives the request context and event processor for sending responses.

**GraphAIAgent**: Koog's graph-based agent implementation. Define your agent logic as nodes (processing steps) connected by edges (transitions).

**Prompt DSL**: Type-safe Kotlin DSL for building prompts:
```kotlin
prompt("joke-generation") {
    system { +"You are a helpful assistant" }
    user { +"Tell me a joke" }
}
```

**MultiLLMPromptExecutor**: Unified interface for executing prompts across different LLM providers (OpenAI, Anthropic, Google, etc.).

**nodeLLMRequestStructured**: Creates a graph node that calls the LLM and parses the response into a structured Kotlin data class using the `@LLMDescription` annotation.

**A2AAgentServer plugin**: Koog plugin that integrates A2A functionality into your GraphAIAgent, providing access to message storage, task storage, and event processors.

### Getting Started with Koog

To build your own A2A agent with Koog:

1. **Add Koog dependencies** (see [build.gradle.kts](./build.gradle.kts))
2. **Create an AgentExecutor** to handle incoming A2A requests
3. **Define an AgentCard** describing your agent's capabilities
4. **Set up the A2A server** with HTTP transport
5. **For simple agents**: Use prompt executor directly with message storage
6. **For complex agents**: Use GraphAIAgent with the A2AAgentServer plugin

See the code comments in `JokeWriterAgentExecutor.kt` for detailed implementation guidance.

## Learn More

- [Koog GitHub Repository](https://github.com/JetBrains/koog)
- [Koog Documentation](https://koog.ai/)
