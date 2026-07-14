# Hello World Agent

Demonstrates a foundational Agent-to-Agent (A2A) server and client implementation using the A2A Go SDK.

## Overview of Core Files

The sample codebase is structured around three core components.

* `main.go`: Configures and launches the standard `net/http` web server, defines the public and extended `AgentCard` configurations, and sets up the A2A routes and request handler.
* `agent_executor.go`: Implements the `AgentExecutor` interface (`HelloWorldAgentExecutor`) to process incoming requests, manage task lifecycle states, stream progress updates using Go native iterators (`iter.Seq2`), and attach generated text artifacts.
* `test_client.go`: Provides a test client demonstrating how to fetch agent cards and interact with the server via both streaming and non-streaming message requests.

## Prerequisites

- **Go**: Version 1.25 or higher.

## Quick Start

1. **Download Dependencies**

   Download the required modules:

   ```bash
   go mod download
   ```

2. **Start the Server & Run the Test Client**

   Run the A2A agent server and interactive test client locally on port `9999`:

   ```bash
   go run .
   ```

   **Expected Output Snippet**:

   ```bash
   Initializes the A2ACardResolver instance with an HTTP client

    Successfully fetched the public agent card:
    ====================================================
                        AgentCard                      
    ====================================================
    --- General ---
    Name        : Hello World Agent
    Description : Just a hello world agent
    Version     : 0.0.1

    --- Interfaces ---
      [0] http://127.0.0.1:9999  (JSONRPC)

    --- Capabilities ---
    Streaming           : true
    Push notifications  : false
    Extended agent card : true

    ...

    history {
      role: ROLE_USER
      parts {
        text: "Say hello."
      }
    }

    history {
      role: ROLE_AGENT
      parts {
        text: "Processing request..."
      }
    }
    ...
    artifacts {
      parts {
        text: "Hello, World! I have received your request (Say hello.)"
        media_type: "text/plain"
      }
    }
    ...
    task_state: TASK_STATE_COMPLETED
    message {
      parts {
        text: "Request is completed!"
      }
    }
    ...
   ```

## Usage

### Building a Container Image

The agent can also be packaged and run using a container image.

1. **Navigate to the Agent Directory**:

   ```bash
   cd samples/go/agents/helloworld
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
