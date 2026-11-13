# Currency Agent using ADK+Skills+A2A v1.0

A currency conversion agent built using the [Google Agent Development Kit (ADK)](https://github.com/google/adk) with Agent Skills and support for A2A v1.0 Protocol.


## Features

- Currency conversion between multiple supported currencies using Frankfurter SKILL.md
- A2A (Agent-to-Agent) v1.0 protocol support.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager.
- A valid Google API Key with access to Gemini models.

## Setup

1. **Switch to the agent directory:**
    ```bash
    cd adk_skills_agent
    ```

2. **Set the Google API Key:**
    ```bash
    export GOOGLE_API_KEY="your-google-api-key"
    ```

3. **Install dependencies:**
    ```bash
    uv sync
    ```

## Running the Server

You can start the A2A agent server using the following command:

```bash
uv run skills_agent
```

## API Endpoints

- **Agent Card:** `GET http://localhost:10999/.well-known/agent-card.json`
- **A2A Endpoint:** `POST http://localhost:10999/`


## Example Requests

[test.http](test.http) has examples for JSONRPC requests for invoking the agent