# SAP Maintenance Order Agent with A2A Protocol

This sample demonstrates an SAP S/4HANA Maintenance Order agent built with
[LangGraph](https://langchain-ai.github.io/langgraph/) and exposed through the
A2A protocol. It showcases the **PEOS (Planner→Executor→Observer→Synthesiser)**
architecture pattern for multi-step enterprise data analysis with dynamic tool
binding and token optimization.

## How It Works

This agent uses a 4-node LangGraph state machine to analyze SAP plant maintenance
data through 11 OData tools. The A2A protocol enables standardized interaction with
the agent, allowing clients to send natural language queries about maintenance
orders, equipment, costs, and confirmations.

```
User ──► A2A Server ──► Planner ──► Executor (loop) ──► Observer ──► Synthesiser ──► Response
                           │            │
                           │       Tool Calls (11 SAP OData tools)
                           │
                     Dynamic Tool Binding
                     (only relevant tools per query)
```

## Key Features

- **PEOS Architecture**: 4 specialized LLM stages instead of one monolithic prompt
- **Dynamic Tool Binding**: Planner selects only relevant tools per query (60-80%
  token reduction)
- **11 SAP OData Tools**: Maintenance orders, equipment, stock, costs,
  confirmations, notifications, purchase orders
- **HITL Write Safety**: Human-in-the-loop confirmation for destructive operations
  (TECO/UNTECO)
- **Mock Data Included**: Runs entirely offline with realistic SAP response data
- **Any LLM Provider**: Uses LiteLLM for OpenAI, Anthropic, Google, Azure, or
  local models
- **Streaming Support**: Real-time status updates during processing

## Prerequisites

- Python 3.12 or higher
- [UV](https://docs.astral.sh/uv/)
- An LLM API key (OpenAI, Anthropic, Google, etc.)

## Setup & Running

1. Navigate to the sample directory:

   ```bash
   cd samples/python/agents/sap_maintenance
   ```

2. Create an environment file:

   ```bash
   echo "OPENAI_API_KEY=your_key_here" > .env
   echo "LLM_MODEL=gpt-4o-mini" >> .env
   ```

   Or for Anthropic:

   ```bash
   echo "ANTHROPIC_API_KEY=your_key_here" > .env
   echo "LLM_MODEL=anthropic/claude-sonnet-4-20250514" >> .env
   ```

3. Run the agent:

   ```bash
   # Default port 10020
   uv run app

   # Custom host/port
   uv run app --host 0.0.0.0 --port 8080
   ```

4. In a separate terminal, test with curl:

   ```bash
   curl -X POST http://localhost:10020 \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": "1",
       "method": "message/send",
       "params": {
         "message": {
           "kind": "message",
           "messageId": "msg-001",
           "role": "user",
           "parts": [{"kind": "text", "text": "Show high priority orders for plant 1010"}]
         }
       }
     }'
   ```

## Build Container Image

1. Navigate to the sample directory:

   ```bash
   cd samples/python/agents/sap_maintenance
   ```

2. Build the container:

   ```bash
   podman build . -t sap-maintenance-a2a-server
   ```

3. Run the container:

   ```bash
   podman run -p 10020:10020 \
     -e OPENAI_API_KEY=your_key_here \
     sap-maintenance-a2a-server
   ```

## SAP OData Tools

| Tool | SAP API | Description |
|------|---------|-------------|
| `search_maintenance_orders` | `API_MAINTENANCEORDER` | Search with 12+ filter dimensions |
| `get_maintenance_order` | `API_MAINTENANCEORDER` | Full order detail with operations |
| `get_work_order_cost_table` | `API_MAINTENANCEORDER` | Cost breakdown by category |
| `get_work_order_confirmation` | `API_MAINTENANCEORDER` | Time confirmations and progress |
| `get_equipment_details` | `API_EQUIPMENT` | Equipment master data |
| `get_material_stock` | `API_MATERIAL_STOCK` | Plant-level stock availability |
| `get_maintenance_notification` | `API_MAINTNOTIFICATION` | Maintenance notifications |
| `get_missing_confirmations_batch` | `API_MAINTENANCEORDER` | Overdue confirmation check |
| `get_material_shortages_batch` | `API_MATERIAL_STOCK` | Shortage detection for components |
| `set_orders_to_teco` | `API_MAINTENANCEORDER` | TECO with HITL confirmation |
| `reset_orders_teco` | `API_MAINTENANCEORDER` | Reverse TECO with HITL |

All APIs are publicly documented on [SAP API Business Hub](https://api.sap.com/).
Mock data is included — no SAP system required to run the sample.

## PEOS Architecture

The agent uses four specialized stages instead of one monolithic LLM call:

| Stage | Role | Token Impact |
|-------|------|-------------|
| **Planner** | Classifies intent, selects tools, creates execution plan | Low (3-turn window) |
| **Executor** | Runs tool calls in a retry loop (max 10 iterations) | Variable |
| **Observer** | Validates completeness, decides retry vs. proceed | Low |
| **Synthesiser** | Formats final user-facing response | Low |

Dynamic tool binding means only the tools selected by the Planner are loaded into
the Executor's context, reducing token usage by 60-80% compared to loading all
tools on every call.

## Technical Implementation

- **LangGraph State Machine**: 4-node graph with conditional edges
- **LiteLLM**: Provider-agnostic LLM interface (OpenAI, Anthropic, Google, etc.)
- **Tool Policy Engine**: HITL gating for write operations
- **A2A Protocol Integration**: Full compliance with A2A v1.0 specification
- **Streaming**: Status updates via SSE during multi-step processing

## Limitations

- Uses mock SAP data by default (set `USE_MOCK_DATA=false` for real SAP
  connection)
- Real SAP connection requires OData API access with proper authorization
- Memory is session-based and not persisted between server restarts
- Write operations (TECO) are gated by HITL confirmation

## Learn More

- [A2A Protocol Documentation](https://a2a-protocol.org/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SAP API Business Hub](https://api.sap.com/)
- [SAP Maintenance Order API](https://api.sap.com/api/API_MAINTENANCEORDER)
- [LiteLLM Documentation](https://docs.litellm.ai/)

## Disclaimer

> **Important**: The sample code provided is for demonstration purposes and
> illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production
> applications, it is critical to treat any agent operating outside of your direct
> control as a potentially untrusted entity.
>
> All data received from an external agent—including but not limited to its
> AgentCard, messages, artifacts, and task statuses—should be handled as untrusted
> input. For example, a malicious agent could provide an AgentCard containing crafted
> data in its fields (e.g., description, name, skills.description). If this data is
> used without sanitization to construct prompts for a Large Language Model
> (LLM), it could expose your application to prompt injection attacks. Failure to
> properly validate and sanitize this data before use can introduce security
> vulnerabilities into your application.
>
> Developers are responsible for implementing appropriate security measures, such
> as input validation and secure handling of credentials to protect their systems
> and users.
