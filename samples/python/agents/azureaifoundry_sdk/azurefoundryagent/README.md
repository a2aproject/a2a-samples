# AI Foundry A2A Demo

A demonstration project showcasing the integration of Azure AI Foundry with the Agent-to-Agent (A2A) framework. This project implements an intelligent calendar management agent with the following capabilities:

## Compatibility

This sample uses A2A SDK `>=1.1.2,<2.0`, protobuf message parts, and the A2A 1.0 JSON-RPC binding. Its server, executor, and client must use that SDK contract together.

The Azure backend remains the classic Foundry Agents API with agents, threads, messages, and runs.
The lockfile retains `azure-ai-agents==1.0.0` and `azure-ai-projects==1.0.0b11`.
This is not a migration to Azure AI Projects 2.x or the newer Responses/conversation APIs.
Use a project endpoint supported by the classic SDK. Calendar tool results are simulated and require no Microsoft Graph calendar access.

Live validation on November 16, 2026 used GPT-5 mini `2025-08-07` with an East US 2 Global Standard deployment.
The included client completed both messaging modes and reused conversation context.
A separate request with exact UTC timestamps exercised the availability tool; both calendar tools completed real provider tool-call cycles.
Model quota and deployment availability depend on the subscription and region.

## Offline regression tests

From this directory, install the locked dependencies and run the sample tests:

```bash
uv sync --locked --python 3.12
uv run --python 3.12 --no-sync python -m unittest discover -s tests -v
```

The tests cover imports, server startup, agent-card discovery, protobuf parts, task events, context reuse, provider exceptions, and the included client in both regular and streaming modes. They use the actual A2A SDK and in-process HTTP routes with the Foundry agent mocked. They do not need Azure credentials or make model requests.

## Features

- 🤖 **AI Foundry Integration**: Build intelligent agents using Azure AI Foundry
- 📅 **Calendar Management**: Check schedule availability, get upcoming events
- 🔄 **A2A Framework**: Support agent-to-agent communication and collaboration
- 💬 **Conversation Capabilities**: Natural language processing and multi-turn conversations
- 🛠️ **Tool Integration**: Simulated calendar API tool integration

## Project Structure

```text
├── foundry_agent.py           # AI Foundry calendar agent 
├── foundry_agent_executor.py  # A2A framework executor
├── __main__.py                # Main application
├── pyproject.toml             # Project dependencies 
├── test_client.py             # A2A 1.x client
├── tests/                    # Credential-free regression tests
└── .env.template              # Environment variables template
```

## Quick Start

### 1. Environment Setup

```bash

# Copy environment variables template
cp .env.template .env

# Edit the .env file and fill in your Azure configuration
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync --locked --python 3.12
```

### 3. Configure Azure AI Foundry

Set the following required environment variables in the `.env` file:

```env
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=Your Azure AI Foundry Project Endpoint
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=Your Azure AI Foundry Deployment Model Name
```

Authenticate through an identity supported by `DefaultAzureCredential`, such as an existing Azure CLI login, and grant that identity the required project permissions. A GitHub or Copilot login does not authenticate Azure. Live model requests can incur Azure charges.

### 4. Run the Demo

Open terminal

```bash
# Start Your Azure AI Foundry Agent
uv run --python 3.12 --no-sync python __main__.py --host 127.0.0.1 --port 10007
```

Open another tag in terminal

```bash
# Test 
uv run --python 3.12 --no-sync python test_client.py
```

The client uses `A2A_BASE_URL` when set, otherwise `http://localhost:10007`. It starts a separate conversation for each messaging mode and reuses that conversation for follow-up questions. Health, transport, and failed-task errors propagate instead of being reported as a successful test run.

## Known limits

- Cancellation is not implemented. The executor rejects cancellation requests rather than publishing a false terminal task state while an Azure run continues.
- The classic Azure calls and polling remain synchronous inside the async agent interface. An async Azure SDK migration is separate work.
- Task and conversation mappings are in memory. Restarting the process loses them.
- Live runs create Azure agent and thread objects. Record their IDs and clean up only your test-owned objects after use; server shutdown does not automatically clean up every Azure object.
- Offline tests do not establish that an Azure project, model deployment, region, or permission configuration works. Validate those separately before treating the sample as production-ready.

## Agent Capabilities

### Calendar Management Skills

1. **Check Availability** (`check_availability`)
   - Check schedule arrangements for specific time periods
   - Example: "Am I free tomorrow from 2 PM to 3 PM?"

2. **Get Upcoming Events** (`get_upcoming_events`)
   - Get future calendar events
   - Example: "What meetings do I have today?"

3. **Calendar Management** (`calendar_management`)
   - General calendar management and scheduling assistant
   - Example: "Help me optimize tomorrow's schedule"

### Conversation Examples

```text
User: Hello, can you help me manage my calendar?
Agent: Of course! I'm the AI Foundry calendar agent, and I can help you check schedule availability, view upcoming events, and optimize your schedule. What do you need help with?

User: Am I free tomorrow from 2 PM to 3 PM?
Agent: Let me check your availability for tomorrow from 2 PM to 3 PM...
```

## Technical Architecture

### Core Components

1. **FoundryCalendarAgent**:
   - Core implementation of Azure AI Foundry agent
   - Handles conversation logic and tool calls

2. **FoundryAgentExecutor**:
   - A2A framework executor
   - Handles request routing and state management

3. **A2A Integration**:
   - Agent card definitions
   - Skills and capabilities declarations
   - Message transformation and processing

### Key Features

- **Agent Interface**: Async A2A execution with a classic synchronous Azure backend
- **Error Handling**: Complete exception handling and logging
- **State Management**: Session and thread state management
- **Extensibility**: Easy to add new tools and skills
