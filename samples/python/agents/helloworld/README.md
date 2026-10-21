# Hello World Agent

Demonstrates a foundational Agent-to-Agent (A2A) server and client implementation using the A2A Python SDK.

## Overview of Core Files

The sample codebase is structured around three core components.

* `__main__.py`: Configures and launches the Starlette ASGI web server using Uvicorn, defines the public and extended `AgentCard` configurations, and sets up the A2A routes and request handler.
* `agent_executor.py`: Implements the `AgentExecutor` interface (`HelloWorldAgentExecutor`) to process incoming requests, manage task lifecycle states, stream progress updates, and attach generated text artifacts.
* `test_client.py`: Provides an asynchronous test client demonstrating how to fetch agent cards and interact with the server via both streaming and non-streaming message requests.

## Prerequisites

- **Python**: Version 3.10 or higher.

## Quick Start

1. **Set up a Virtual Environment and Install Dependencies**

   Create and activate a virtual environment, then install the required packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the Server**

   Run the A2A agent server locally on port `9999`:

   ```bash
   python __main__.py
   ```

3. **Run the Test Client**

   In a separate terminal, activate the virtual environment and execute the test client to verify communication with the agent:

   ```bash
   source .venv/bin/activate
   python test_client.py
   ```

   Running `python test_client.py` starts an interactive session and waits at `user >`. Enter a message to send it to the local server; the client prints response events as they arrive. Type `exit` to quit. This interactive entry point does not display the agent card or run the streaming and extended-card demonstrations.

## Usage

### Building a Container Image

The agent can also be packaged and run using a container image.

1. **Navigate to the Agent Directory**:

   ```bash
   cd samples/python/agents/helloworld
   ```

2. **Build the Container Image**:

   ```bash
   podman build . -t helloworld-a2a-server
   ```

   > [!TIP]
   > `podman` is a drop-in replacement for `docker` and can be used interchangeably in these commands.

3. **Run Your Container**:

   ```bash
   podman run -p 9999:9999 helloworld-a2a-server
   ```

### Validating with the CLI Host

To interact with the agent using the sample CLI host, open a separate terminal and run:

```bash
cd samples/python/hosts/cli
uv run . --agent http://127.0.0.1:9999
```

## Disclaimer
**Important:** The sample code provided is for demonstration purposes and
illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building
production applications, it is critical to treat any agent operating outside of
your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its
AgentCard, messages, artifacts, and task statuses—should be handled as untrusted
input. For example, a malicious agent could provide an AgentCard containing
crafted data in its fields (e.g., description, name, skills.description). If
this data is used without sanitization to construct prompts for a Large Language
Model (LLM), it could expose your application to prompt injection attacks.
Failure to properly validate and sanitize this data before use can introduce
security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such
as input validation and secure handling of credentials to protect their systems
and users.
