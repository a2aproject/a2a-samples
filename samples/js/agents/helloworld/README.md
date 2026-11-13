# Hello World Agent (JavaScript/TypeScript)

Demonstrates a foundational Agent-to-Agent (A2A) server and client implementation using the `@a2a-js/sdk` v1.0.

## Overview of Core Files

The sample codebase is structured around three core components.

- `index.ts`: Configures and launches the Express web server, defines the public and extended `AgentCard` configurations, and sets up the A2A routes and request handler on port `9999`.
- `agent_executor.ts`: Implements the `AgentExecutor` interface (`HelloWorldAgentExecutor`) to process incoming requests, manage task lifecycle states, stream progress updates, and attach generated text artifacts.
- `test_client.ts`: Provides a test client demonstrating how to fetch agent cards and interact with the server via both streaming and non-streaming message requests, plus an interactive CLI mode.

## Prerequisites

- **Node.js**: Version 20 or higher.

## Quick Start

1. **Install Dependencies**

    Navigate to the sample directory and install dependencies:

    ```bash
    npm install
    ```

2. **Start the Server**

    Run the A2A agent server locally on port `9999`:

    ```bash
    npm start
    ```

3. **Run the Test Client**

    In a separate terminal, execute the test client to verify communication with the agent:

    ```bash
    npm run client
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
