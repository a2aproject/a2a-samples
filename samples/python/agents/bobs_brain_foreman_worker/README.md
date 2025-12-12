# Bob's Brain: Foreman-Worker Pattern Demo

**Framework:** Google ADK (Agent Development Kit)
**Pattern:** Foreman-Worker Delegation
**Protocol:** A2A 0.3.0

## Overview

This sample demonstrates the complete orchestrator → foreman → worker pattern from [Bob's Brain](https://github.com/jeremylongshore/bobs-brain), a multi-agent ADK compliance department deployed on Vertex AI Agent Engine.

**What this demo shows:**
- **Bob (Orchestrator)** - Global coordinator with LlmAgent reasoning and natural language interface
- **Foreman Agent** - Middle manager using LlmAgent to analyze and route tasks to specialists
- **Worker Agent** - Specialist performing domain tasks (deterministic functions for cost optimization)
- **A2A Communication** - Full chain: Bob → Foreman → Worker with AgentCard discovery
- **Memory Integration** - Session and Memory Bank services (optional, requires GCP project)
- **LLM Reasoning** - Both Bob and Foreman use `agent.run()` for intelligent tool selection

## Architecture Pattern

This demo implements the **production pattern** used in Bob's Brain:

### What This Demo Shows
- ✅ **Bob orchestrator** with LlmAgent for global coordination
- ✅ **Foreman** using `agent.run()` for LLM-based task analysis and routing
- ✅ **Worker** with deterministic tools (no LLM for cost optimization)
- ✅ **Bob ↔ Foreman A2A** communication over HTTP with AgentCards
- ✅ **Foreman ↔ Worker** delegation with skill-based routing
- ✅ **Memory integration** (Session + Memory Bank) when GCP project configured
- ✅ **SPIFFE identity** propagation across all agents
- ✅ **Complete chain**: User → Bob → Foreman → Worker → Response

### Intentional Simplifications
- ⚠️ Single worker instead of 8 specialized workers (production has iam-adk, iam-issue, iam-fix-plan, etc.)
- ⚠️ No Slack integration (production Bob interfaces with Slack)
- ⚠️ Memory disabled by default (enable with `ENABLE_MEMORY=true` and GCP_PROJECT_ID)
- ⚠️ No CI/CD or deployment automation

### Why These Choices?

**Deterministic Workers**: In production Bob's Brain, specialists are deterministic tools without LLM calls. This optimizes cost and ensures consistent behavior. Only Bob (orchestrator) and the foreman (middle manager) use LLMs for reasoning.

**Single Worker**: We implemented one specialist for clarity. Adding more workers follows the same pattern - each exposes an AgentCard with skill schemas.

**LLM Reasoning Layers**: Bob and Foreman both use `agent.run()` to let Gemini analyze natural language input and intelligently choose which tools to invoke. This is the proper ADK pattern for agents that need reasoning capability.

**Memory Integration**: When you set `ENABLE_MEMORY=true` and provide a GCP project ID, both Bob and Foreman use Vertex AI Session Service and Memory Bank Service for conversation context retention.

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Bob Orchestrator                         │
│                      (bob_demo)                             │
│                                                             │
│  Uses: LlmAgent with agent.run()                           │
│  Memory: Session + Memory Bank (optional)                  │
│  Tools:                                                     │
│  - call_foreman: Delegate to department foreman            │
│                                                             │
└────────────────┬────────────────────────────────────────────┘
                 │ A2A Protocol
                 │ (HTTP + AgentCard discovery)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Foreman Agent                          │
│         (iam_senior_adk_devops_lead_demo)                   │
│                                                             │
│  Uses: LlmAgent with agent.run()                           │
│  Memory: Session + Memory Bank (optional)                  │
│  Tools:                                                     │
│  - route_task: Analyze request, select worker              │
│  - coordinate_workflow: Manage multi-step tasks            │
│                                                             │
└────────────────┬────────────────────────────────────────────┘
                 │ A2A Protocol
                 │ (HTTP + AgentCard discovery)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                       Worker Agent                          │
│                  (iam_adk_demo)                             │
│                                                             │
│  Uses: Deterministic Python functions (no LLM)             │
│  Tools:                                                     │
│  - analyze_compliance: Check ADK pattern compliance        │
│  - suggest_fix: Recommend improvements                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts Demonstrated

### 1. Foreman-Worker Delegation
The foreman agent receives complex requests and routes them to the appropriate specialist worker based on:
- Skill requirements (from worker AgentCards)
- Task complexity
- Current workload

### 2. AgentCard Discovery
Each agent publishes an AgentCard (A2A 0.3.0) describing:
- Available skills with input/output schemas
- SPIFFE identity for secure routing
- Capabilities and constraints

### 3. Production Patterns
This demo shows simplified versions of patterns used in the full Bob's Brain system:
- **In Production:** 1 orchestrator + 1 foreman + 8 specialist workers
- **This Demo:** 1 foreman + 1 worker (minimal viable example)

## How This Relates to Production

### This Demo
```text
User → HTTP → Bob (LlmAgent) → A2A → Foreman (LlmAgent) → A2A → Worker (1 specialist)
               ↓                       ↓                          ↓
           agent.run()             agent.run()            deterministic tools
           (reasons)               (routes)               (executes)
```

### Production Bob's Brain
```text
User → Slack → Bob (LlmAgent) → A2A → Foreman (LlmAgent) → A2A → 8 Workers
               ↓ Memory                ↓ Memory                    ├─ iam-adk
               Session +               Session +                   ├─ iam-issue
               Memory Bank             Memory Bank                 ├─ iam-fix-plan
                                                                   ├─ iam-fix-impl
                                                                   ├─ iam-qa
                                                                   ├─ iam-doc
                                                                   ├─ iam-cleanup
                                                                   └─ iam-indexer
```

### Key Differences

| Feature | This Demo | Production |
|---------|-----------|------------|
| **Bob Orchestrator** | ✅ Full implementation with LlmAgent | ✅ Full implementation with Slack integration |
| **Foreman LLM** | ✅ Uses `agent.run()` for routing | ✅ Uses `agent.run()` for routing |
| **A2A Protocol** | ✅ Full chain: Bob ↔ Foreman ↔ Worker | ✅ Full chain with all agents |
| **Memory** | ✅ Optional (disabled by default) | ✅ Always enabled (Session + Memory Bank) |
| **Specialists** | 1 worker (demo simplification) | 8 specialized workers |
| **Deployment** | Local demo (3 processes) | Vertex AI Agent Engine (us-central1) |

## Full Production System

Bob's Brain is a complete ADK compliance department with:
- **10 Agents:** bob (orchestrator) → iam-senior-adk-devops-lead (foreman) → 8 specialist workers
- **Production Deployment:** Vertex AI Agent Engine (us-central1)
- **Hard Mode Compliance:** R1-R8 architectural rules enforced via CI
- **95/100 Quality Score:** 145 docs, 65%+ test coverage, 28 canonical standards

**Repository:** https://github.com/jeremylongshore/bobs-brain
**Release:** v0.13.0
**Linux Foundation AI Card Reference:** https://github.com/Agent-Card/ai-card/pull/7

## Running This Demo

### Prerequisites
```bash
pip install -r requirements.txt
```

### Option 1: Full Chain (Bob → Foreman → Worker)

**Terminal 1 - Start Worker:**
```bash
python worker_agent.py
# Worker running on localhost:8001
```

**Terminal 2 - Start Foreman:**
```bash
python foreman_agent.py
# Foreman running on localhost:8000
# Discovers worker at localhost:8001/.well-known/agent-card.json
```

**Terminal 3 - Start Bob:**
```bash
python bob_agent.py
# Bob running on localhost:8002
# Discovers foreman at localhost:8000/.well-known/agent-card.json
```

**Terminal 4 - Send Request to Bob:**
```bash
curl -X POST http://localhost:8002/task \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Analyze our ADK agent for compliance issues with the lazy-loading pattern"
  }'
```

The complete flow:
1. **Bob** receives natural language request
2. **Bob's LlmAgent** uses `agent.run()` to analyze and chooses to call `call_foreman` tool
3. **Foreman** receives task from Bob via A2A
4. **Foreman's LlmAgent** uses `agent.run()` to choose `route_task` tool
5. **Worker** receives specific task and executes deterministic analysis
6. **Results flow back**: Worker → Foreman → Bob → User

### Option 2: Direct to Foreman (Skip Bob)

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Analyze code for ADK compliance"
  }'
```

### Option 3: Enable Memory (Requires GCP Project)

```bash
export ENABLE_MEMORY=true
export GCP_PROJECT_ID=your-gcp-project
export GCP_REGION=us-central1

# Then start agents as usual
python bob_agent.py
python foreman_agent.py
python worker_agent.py
```

## AgentCards

All three agents publish A2A AgentCards at `/.well-known/agent-card.json`:

**Bob AgentCard:**
- Skills: `process_request` (natural language interface)
- SPIFFE ID: `spiffe://demo.intent.solutions/agent/bob/dev/us-central1/0.1.0`
- Capabilities: orchestration, natural_language_interface, foreman_delegation

**Foreman AgentCard:**
- Skills: `route_task`, `coordinate_workflow`
- SPIFFE ID: `spiffe://demo.intent.solutions/agent/foreman/dev/us-central1/0.1.0`
- Capabilities: task_routing, workflow_orchestration, worker_delegation

**Worker AgentCard:**
- Skills: `analyze_compliance`, `suggest_fix`
- SPIFFE ID: `spiffe://demo.intent.solutions/agent/adk-worker/dev/us-central1/0.1.0`
- Capabilities: adk_expertise, compliance_analysis, fix_suggestions

## Learning Resources

- **Full Production System:** https://github.com/jeremylongshore/bobs-brain
- **ADK Documentation:** https://cloud.google.com/vertex-ai/docs/agent-development-kit
- **A2A Protocol Spec:** https://github.com/a2aproject/a2a-protocol
- **SPIFFE Identity:** https://spiffe.io/

## Contributing

This is a demonstration example. For production-grade patterns and real-world usage, see the full Bob's Brain repository.

**Questions?**
- **Full System:** https://github.com/jeremylongshore/bobs-brain
- **Contact:** jeremy@intentsolutions.io

---

**Status:** Educational Demo (Simplified Production Pattern)
**Based On:** Bob's Brain v0.13.0
**License:** Apache 2.0
