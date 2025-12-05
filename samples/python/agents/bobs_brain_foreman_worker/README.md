# Bob's Brain: Foreman-Worker Pattern Demo

**Framework:** Google ADK (Agent Development Kit)
**Pattern:** Foreman-Worker Delegation
**Protocol:** A2A 0.3.0

## Overview

This is a simplified demonstration of the foreman-worker architectural pattern used in production by [Bob's Brain](https://github.com/jeremylongshore/bobs-brain), a multi-agent ADK compliance department deployed on Vertex AI Agent Engine.

**What this demo shows:**
- **Foreman Agent** - Routes tasks to specialist workers based on skill requirements
- **Worker Agent** - Performs specific domain tasks (ADK compliance analysis)
- **A2A Communication** - Clean agent-to-agent delegation using AgentCards
- **Production Pattern** - Simplified version of real production architecture

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

## Production Differences

| Feature | This Demo | Production Bob's Brain |
|---------|-----------|----------------------|
| **Agents** | 2 (foreman + 1 worker) | 10 (orchestrator + foreman + 8 workers) |
| **Deployment** | Local (demo) | Vertex AI Agent Engine |
| **AgentCards** | Simplified | Full A2A 0.3.0 with trust attestations |
| **Tools** | Minimal (demo) | GitHub, Terraform, Vertex AI Search, etc. |
| **Memory** | None (stateless demo) | Dual memory (Session + Memory Bank) |
| **CI/CD** | None | 8 GitHub Actions workflows with drift detection |

## Contributing

This is a demonstration example. For production-grade patterns and real-world usage, see the full Bob's Brain repository.

**Questions?**
- **Full System:** https://github.com/jeremylongshore/bobs-brain
- **Contact:** jeremy@intentsolutions.io

---

**Status:** Educational Demo (Simplified Production Pattern)
**Based On:** Bob's Brain v0.13.0
**License:** Apache 2.0
