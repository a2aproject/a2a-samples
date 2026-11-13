# AG2 Mypy tool Agent with A2A Protocol

This sample demonstrates an AG2 agent that is exposed through the A2A protocol. It shows how an AG2 can communicate
using A2A as a lingua franca, which is helpful for building a distributed agent system where different agents
can communicate with each other using the A2A protocol. The agent-as-a-service architecture allows you to encapsulate agent logic,
the local environment, tools, and other capabilities into a separate service that can be reused in different agent workflows.

Here is a sequence diagram that shows how the current demo implementation of the A2A protocol works:

```mermaid
sequenceDiagram
    participant Client as AG2 CodeGen Agent (A2A Client)
    participant Server as A2A Server (JSON-RPC)
    participant Agent as AG2 Reviewer Agent (LLM + Tools)
    participant Tool as Mypy Tool

    Client->>Server: Fetch agent card, then send task with generated code
    Server->>Agent: Forward task to AG2 agent
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

Here we have a simple demo that shows how to use the A2A protocol to communicate with an AG2 agent. We have
- one A2A-served remote agent `a2a_python_reviewer.py`, built with `A2AServer` and exposed over JSON-RPC
- two different A2A clients, which communicate with the remote agent using the A2A protocol:
    CLI code generator `cli_codegen_a2a_client.py` and FastAPI code generator `fastapi_codegen_a2a_client.py`

On the client side the remote reviewer is just an `Agent` configured with `A2AConfig`, and `Agent.as_tool()`
turns it into a regular tool of the local code generator agent. The local LLM decides when to delegate the
generated code for review, and the delegation goes over A2A.

The sample targets **AG2 v1.0.0+** (the `ag2` package). It is not compatible with the pre-1.0 `autogen` API.

## Prerequisites

- Python 3.12 or higher
- UV package manager
- OpenAI API Key (for default configuration)
- AG2 v1.0.0 or higher

## Setup & Running

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/ag2
    ```

2. Export your API key (the sample uses `openai gpt-5.6-luna`):

    ```bash
    export OPENAI_API_KEY=your_api_key_here
    ```

3. Install the dependencies:
    ```bash
    uv sync
    ```

4. Run the remote agent:
    ```bash
    uv run a2a_python_reviewer.py
    ```

5. In a new terminal (with `OPENAI_API_KEY` exported as well), start an A2AClient interface to interact with the remote (ag2) agent. You can use one of the following clients:

    - **Method A: Run the CLI client**

        ```bash
        uv run cli_codegen_a2a_client.py
        ```

    - **Method B: Run the FastAPI client**

        ```bash
        uv run fastapi_codegen_a2a_client.py
        ```

## Learn More

- [A2A Protocol Documentation](https://google.github.io/A2A/#/documentation)
- [AG2 Documentation](https://docs.ag2.ai/)
- [AG2 A2A Documentation](https://docs.ag2.ai/docs/user-guide/a2a/overview)

## Disclaimer

> [!WARNING]
> **The sample code provided is for demonstration purposes only.** When building production applications, it is critical
> to treat any agent operating outside of your direct control as a potentially untrusted entity.
>
> All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., `description`, `name`, `skills.description`).
> If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks. Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.
>
> Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials, to protect their systems and users.
