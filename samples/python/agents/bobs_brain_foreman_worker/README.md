# Bob's Brain: Foreman-Worker Pattern Demo

**Framework:** Google ADK (Agent Development Kit)
**Pattern:** Foreman-Worker Delegation
**Protocol:** A2A 0.3.0

## Overview

This sample demonstrates the foreman-worker delegation pattern from [Bob's Brain](https://github.com/jeremylongshore/bobs-brain), a multi-agent ADK compliance department deployed on Vertex AI Agent Engine.

**What this demo shows:**
- **Foreman Agent** - Analyzes requests and routes tasks to specialist workers
- **Worker Agent** - Performs specific domain tasks (ADK compliance analysis)
- **A2A Communication** - Service discovery via AgentCards and HTTP-based delegation
- **Separation of Concerns** - Clear boundaries between coordination and execution

## Scope and Limitations

This is a simplified demonstration of patterns from the production system:

### Current Implementation
- ✅ Foreman and worker agents with AgentCards (A2A 0.3.0)
- ✅ HTTP-based task delegation (Foreman → Worker)
- ✅ Deterministic specialist functions (cost-optimized)
- ⚠️ Foreman's `LlmAgent` instantiated but Flask routes call tools directly
- ⚠️ No Bob orchestrator layer (demo starts at foreman level)

### Not Yet Demonstrated
- [ ] Foreman routing requests through `agent.run()` for LLM-based tool selection
- [ ] Bob (orchestrator) → Foreman A2A communication
- [ ] Multiple specialist workers (production has 8)
- [ ] Memory integration (Session + Memory Bank)
- [ ] CI/CD and deployment automation

### Why These Choices?

**Deterministic Workers**: In production Bob's Brain, specialists are deterministic tools without LLM calls. This optimizes cost and ensures consistent behavior. Only Bob (orchestrator) and the foreman (middle manager) use LLMs for reasoning.

**Single Worker**: We implemented one specialist for clarity. Adding more workers follows the same pattern - each exposes an AgentCard with skill schemas.

**Foreman Tool Selection**: The current implementation calls tools directly. A future refactor will route through `agent.run()` to let the LLM analyze natural language input and choose appropriate tools dynamically.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Foreman Agent                          │
│         (iam_senior_adk_devops_lead_demo)                   │
│                                                             │
│  Skills:                                                    │
│  - route_task: Analyze request, select worker              │
│  - coordinate_workflow: Manage multi-step tasks            │
│                                                             │
└────────────────┬────────────────────────────────────────────┘
                 │ A2A Protocol
                 │ (AgentCard-based delegation)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                       Worker Agent                          │
│                  (iam_adk_demo)                             │
│                                                             │
│  Skills:                                                    │
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
```
User → HTTP → Foreman → HTTP → Worker (1 specialist)
                 ↓
           (LlmAgent created but not used)
```

### Production Bob's Brain
```
User → Slack → Bob (LlmAgent) → A2A → Foreman (LlmAgent) → A2A → 8 Workers
                                                                    ├─ iam-adk
                                                                    ├─ iam-issue
                                                                    ├─ iam-fix-plan
                                                                    ├─ iam-fix-impl
                                                                    ├─ iam-qa
                                                                    ├─ iam-doc
                                                                    ├─ iam-cleanup
                                                                    └─ iam-indexer
```

### Key Differences

| Feature | This Demo | Production |
|---------|-----------|------------|
| **Entry Point** | Direct HTTP to Foreman | Bob orchestrator with Slack integration |
| **Foreman LLM** | Instantiated but bypassed | Actively uses `agent.run()` for routing |
| **A2A Protocol** | AgentCards + HTTP delegation | Full A2A with Bob ↔ Foreman communication |
| **Specialists** | 1 worker (demo) | 8 specialized workers |
| **Memory** | None (stateless) | Dual memory (Session + Memory Bank) |
| **Deployment** | Local demo | Vertex AI Agent Engine (us-central1) |

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

### Start the Worker Agent
```bash
python worker_agent.py
# Worker running on localhost:8001
```

### Start the Foreman Agent
```bash
python foreman_agent.py
# Foreman running on localhost:8000
# Discovers worker via AgentCard at localhost:8001/.well-known/agent-card.json
```

### Send a Task
```bash
curl -X POST http://localhost:8000/route_task \
  -H "Content-Type: application/json" \
  -d '{
    "task": "analyze_adk_compliance",
    "context": "Check if agents follow ADK lazy-loading pattern"
  }'
```

The foreman will:
1. Analyze the task requirements
2. Query worker AgentCard for capabilities
3. Delegate to the worker via A2A protocol
4. Aggregate results and return

## AgentCards

Both agents publish A2A AgentCards at `/.well-known/agent-card.json`:

**Foreman AgentCard:**
- Skills: `route_task`, `coordinate_workflow`
- SPIFFE ID: `spiffe://demo.intent.solutions/agent/foreman/dev/us-central1/0.1.0`

**Worker AgentCard:**
- Skills: `analyze_compliance`, `suggest_fix`
- SPIFFE ID: `spiffe://demo.intent.solutions/agent/adk-worker/dev/us-central1/0.1.0`

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
