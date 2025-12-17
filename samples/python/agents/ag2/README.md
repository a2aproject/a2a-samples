# AG2 Mypy tool Agent with A2A Protocol

This sample demonstrates an AG2 agent that is exposed through the A2A protocol. It shows how an AG2 can communicate
using A2A as a lingua franca, which is helpful for building a distributed agent system where different agents
can communicate with each other using the A2A protocol. The agent-as-a-service architecture allows you to encapsulate agent logic,
the local environment, tools, and other capabilities into a separate service that can be reused in different agent workflows.

Here is a sequence diagram that shows how the current demo implementation of the A2A protocol works:

```mermaid
sequenceDiagram
    participant Client as A2A Client
    participant Server as A2A Server
    participant Agent as AG2 (LLM + MCP Client)
    participant Tool as Mypy Tool

    Client->>Server: Send task with query
    Server->>Agent: Forward query to AG2 agent
    Note over Server,Agent: Real-time status updates (streaming)

    Agent->>Agent: LLM decides to use tool
    Agent->>Tool: Send tool execution request
    Tool->>Agent: Return tool results

    Agent->>Agent: LLM processes tool results
    Agent->>Server: Return completed response
    Server->>Client: Respond with task results
```

## Possible use cases for Agent-as-a-Service architecture

- **Tool Access**: Leverage various MCP or custom tools for complex tasks.
- **Web Browsing**: Access to web browsing capabilities.
- **Code Execution**: Run Python code for data analysis tasks.
- **Image Generation**: Create images from text descriptions.
- **Real-time Streaming**: Get status updates during processing.
- **Cross-Framework Communication**: Demonstrates A2A's ability to connect different agent frameworks.

## The demo

This demo shows how to use the A2A protocol to communicate with an AG2 agent using a **server-client architecture**:

### Server Side

**`a2a_python_reviewer.py`** - The A2A server that runs the ReviewerAgent

**What it does:**
- Creates a `ReviewerAgent` that reviews Python code for type correctness
- Registers a `mypy-checker` tool for code validation
- Exposes the agent via A2A protocol on `http://localhost:8000`
- Acts as a reusable code review service

**🚀 Run this first** - it must be running before any client can connect.

### Client Side

Pick **one** of the following clients based on what you want to generate:

#### Option 1: `fastapi_codegen_a2a_client.py`
**Purpose:** Generate FastAPI REST APIs with automated review

**What it does:**
- Creates a local `CodeGenAgent` specialized in FastAPI development
- Connects to the remote `ReviewerAgent` via A2A protocol
- Generates FastAPI code and iterates with the reviewer until type-checking passes

**Use when:** You need to generate web APIs

#### Option 2: `cli_codegen_a2a_client.py`
**Purpose:** Generate command-line scripts with automated review

**What it does:**
- Creates a local `CodeGenAgent` specialized in CLI tools (argparse)
- Connects to the remote `ReviewerAgent` via A2A protocol
- Generates CLI scripts and iterates with the reviewer until type-checking passes

**Use when:** You need to generate command-line tools

### Optional: WebSocket Demo UI

For visual demonstrations only (not required for A2A):

- `websocket.py` - FastAPI server with WebSocket wrapper
- `demo-ui/` - Pixel-art themed browser interface with live updates

## Prerequisites

- Python 3.12 or higher
- UV package manager
- OpenAI API Key (for default configuration)

## Setup & Running

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/ag2
    ```

2. Create an environment file with your API key (uses `openai gpt-4o`):

    ```bash
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    ```

3. Install the dependencies:
    ```bash
    uv sync
    ```

4. Run the remote agent:
    ```bash
    uv run a2a_python_reviewer.py
    ```

5. In a new terminal, start an A2A client to interact with the remote ReviewerAgent. You can use one of the following:

    - **Method A: CLI code generator client**

        ```bash
        uv run cli_codegen_a2a_client.py
        ```
        
        Generates CLI scripts and sends them to the reviewer for type checking.

    - **Method B: FastAPI code generator client**

        ```bash
        uv run fastapi_codegen_a2a_client.py
        ```
        
        Generates FastAPI applications and sends them to the reviewer for type checking.

    - **Method C: WebSocket demo UI (optional - for visual demos)**

        ```bash
        uv run websocket.py
        ```
        
        Then open `http://127.0.0.1:9000/` in your browser for a pixel-art themed interactive demo.

## Learn More

- [A2A Protocol Documentation](https://google.github.io/A2A/#/documentation)
- [AG2 Documentation](https://docs.ag2.ai/)
- [AG2 A2A Documentation](https://docs.ag2.ai/latest/docs/user-guide/a2a/)
- [MCP Documentation](https://modelcontextprotocol.io/introduction)

## Disclaimer

> [!WARNING]
> **The sample code provided is for demonstration purposes only.** When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.
>
> All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., `description`, `name`, `skills.description`).
> If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks. Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.
>
> Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials, to protect their systems and users.
