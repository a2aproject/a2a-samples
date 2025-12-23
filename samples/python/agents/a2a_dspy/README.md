
# A2A DSPy Agent with Memory

This sample demonstrates an Agent-to-Agent (A2A) server built using [DSPy](https://github.com/stanfordnlp/dspy), a framework for programming with language models. The agent features conversational memory powered by [Mem0](https://mem0.ai/) and observability through [Braintrust](https://www.braintrust.dev/).

## Core Functionality

* **DSPy Integration:** Uses DSPy's `ChainOfThought` module for structured reasoning and response generation.
* **Memory Management:** Leverages Mem0 to store and retrieve user interactions, enabling context-aware conversations across sessions.
* **Observability:** Integrated with Braintrust for tracing agent execution, LLM calls, and memory operations.
* **A2A Protocol:** Fully compliant A2A server that supports both stateful conversations and task completion.

## Files

* `__main__.py`: The main entry point that configures and starts the A2A server with CORS support.
* `executor.py`: The `DspyAgentExecutor` class that implements the A2A `AgentExecutor` interface, handling task execution and memory operations.
* `agents/dspy_example.py`: DSPy agent definition using a custom `AgentSignature` with Chain-of-Thought reasoning.
* `memory/base.py`: Abstract base class for memory implementations.
* `memory/mem0.py`: Mem0 memory implementation for storing and retrieving conversation context.
* `logger.py`: Logging configuration for the agent.
* `test_client.py`: Test client to interact with the agent.

## Prerequisites

* Python 3.13
* OpenAI API Key
* Mem0 API Key
* Braintrust API Key (optional, for observability)

## Setup

1. **Set Environment Variables:**

   Create a `.env` file or export the following environment variables:

   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export MEM0_API_KEY="your-mem0-api-key"
   export BRAINTRUST_API_KEY="your-braintrust-api-key"  # Optional
   ```

   Replace the placeholder values with your actual API keys.

2. **Install Dependencies:**

   The project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`.

## Running the Application

1. **Start the A2A Server:**

   ```bash
   uv run .
   ```

   By default, the server will start on `http://localhost:10020`. You can customize the host and port:

   ```bash
   uv run . --host 0.0.0.0 --port 8080
   ```

2. **Interact with the Agent:**

   You can use the included test client:

   ```bash
   uv run test_client.py
   ```

   Or use the CLI host from the samples:

   ```bash
   cd samples/python/hosts/cli
   uv run . --agent http://localhost:10020
   ```

## How It Works

1. **User Input:** The agent receives a question or message through the A2A protocol.
2. **Memory Retrieval:** The agent queries Mem0 for relevant past interactions using the user's context ID.
3. **DSPy Processing:** The question and retrieved context are passed to the DSPy `ChainOfThought` module.
4. **Response Generation:** DSPy generates a response using GPT-4o-mini, determining if the task is complete or requires more input.
5. **Memory Storage:** The interaction (user input and agent response) is saved to Mem0 for future context.
6. **Task Completion:** The agent either completes the task with an artifact or requests additional input.

## Agent Capabilities

The agent exposes a single skill:

* **Skill ID:** `dspy_agent`
* **Name:** DSPy Agent
* **Description:** A simple DSPy agent that can answer questions and remember user interactions.
* **Tags:** DSPy, Memory, Mem0
* **Example Queries:**
  - "What is the capital of France?"
  - "What did I ask you about earlier?"
  - "Remember that I prefer morning meetings."

## Memory Features

The agent uses Mem0 to provide:

* **User-specific Memory:** Each user (identified by `context_id`) has their own memory space.
* **Semantic Retrieval:** Memories are retrieved based on semantic similarity to the current query.
* **Persistent Context:** Conversations are remembered across sessions, enabling continuity.

## Observability

With Braintrust integration, you can:

* Track each agent execution with detailed spans
* Monitor LLM calls and their inputs/outputs
* View memory retrieval and storage operations
* Analyze performance and debug issues

Visit the Braintrust dashboard to view traces after interacting with the agent.

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input.
For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description).
If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.
Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
