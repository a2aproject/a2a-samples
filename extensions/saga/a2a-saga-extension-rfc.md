---
title: A2A-SAGA — Saga Orchestration Extension for Agent2Agent (A2A)
status: Draft
category: Standards Track (A2A Extension)
version: 1
extension_uri: https://a2a.dev/extensions/saga/v1
proposed_by: origo Labs (GitHub: @origo-labs)
last_updated: 2026-01-01
---

## 1. Abstract

This document specifies **A2A-SAGA**, an extension to the Agent2Agent (A2A) protocol that standardizes **saga-style orchestration** for multi-agent workflows.

A2A-SAGA defines interoperable, on-the-wire semantics for:

- executing multi-step workflows across agents,
- determining whether actions took effect (including uncertain outcomes),
- compensating previously completed actions when later steps fail,
- safe retries via idempotency, and
- parallel step execution with deterministic recovery ordering.

This RFC is **fully self-contained**: all protocol rules, JSON Schemas, and normative test vectors required for conformance are included.

## 2. Motivation

As agents evolve from conversational assistants into autonomous actors, they increasingly perform **state-changing actions** across external systems: creating records, provisioning infrastructure, modifying configurations, and sending notifications.

The reliability challenge is not merely issuing actions, but **knowing what actually happened** and recovering safely when actions fail or outcomes are uncertain.

### 2.1 The Need for Specialized Verbs

While the A2A Core `Message` object handles conversational turns effectively, it lacks the semantic precision required for reliable distributed transactions. Overloading the generic `Message` with unstructured metadata creates brittle, unvalidatable contracts.

A2A-SAGA introduces explicit JSON-RPC verbs (`saga.step.execute`, `saga.step.verify`, `saga.step.compensate`) to strictly define the lifecycle of a transaction. This ensures that:

1. **Intent is Unambiguous:** A `compensate` request cannot be mistaken for a new task.
2. **Validation is Enforceable:** Schemas can strictly enforce `idempotency_key` presence for state-changing operations, which is optional in generic messages.
3. **Tooling is Robust:** Middleware can automatically route saga steps to specific queues or audit logs based on the method name alone, without parsing payload bodies.


### 2.2 Outcome Uncertainty & Partial Completion

In real systems, outcomes such as _unknown_ are unavoidable due to timeouts and asynchronous processing. Multi-step workflows also encode invariants (e.g., “if X exists, Y must exist”). When a later step fails, earlier successful actions can leave systems in an unacceptable intermediate state.

A2A-SAGA standardizes the **Compensation Pattern**: best-effort undo/mitigation to restore acceptable invariants, rather than perfect rollback.

## 3. Goals and Non-Goals

### 3.1 Goals

- Interoperable saga orchestration across A2A agents.
- Explicit, observable outcomes (`succeeded`, `failed`, `unknown`).
- Safe retries via mandated idempotency.
- Deterministic compensation ordering (including parallel steps).
- **Discovery:** Standardized advertisement of saga roles via the Agent Card.

### 3.2 Non-Goals

- Atomic multi-party commit guarantees (2PC/XA).
- Distributed consensus or leader election.
- Standardization of agent internal reasoning/planning.
- Byzantine fault tolerance.

## 4. Terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as described in RFC 2119.

- **Saga:** Ordered workflow of steps with compensation semantics.
- **Orchestrator:** A _role_ coordinating a saga.
- **Participant:** Agent executing steps.
- **Compensation:** Best-effort undo or mitigation.
- **Verification:** Operation to determine whether an effect occurred.
- **Protocol Error:** A failure in the RPC mechanics (e.g., malformed JSON, missing header).
- **Application Error:** A valid RPC call resulting in a logical failure (e.g., "Out of Stock").

## 5. Extension Identification and Activation

**Extension URI:** `https://a2a.dev/extensions/saga/v1`

### 5.1 Header Negotiation (Normative)

Clients invoking any method defined in this specification (`saga.*`) MUST include the `A2A-Extensions` HTTP header (or equivalent transport metadata). The header value is a comma-separated list of extension URIs to activate for the request (see `extensions/extensions.md`).

- **Header Name:** `A2A-Extensions`
  - **Legacy Alias:** Implementations MAY also accept `X-A2A-Extensions` for backward compatibility only. The `X-` prefix is deprecated by RFC 6648.
- **Header Value:** Must contain the Extension URI as one item in the comma-separated list.
  - _Example:_ `A2A-Extensions: https://a2a.dev/extensions/saga/v1`

**Server Behavior:**

1. If the header is present and the server supports the extension, it MUST process the request according to this RFC.

2. If the header is **missing** or does not include this extension URI, and the client invokes a `saga.*` method, the server MUST reject the request with JSON-RPC error code `-32601` (Method not found) or a specific extension error `-32001` (Extension required).
   - If the Agent Card declares the extension as `required: true`, the server SHOULD use `-32001` to make the requirement explicit.


### 5.2 Discovery: Agent Card Declaration (Normative)

Agents supporting this extension MUST advertise their capabilities in the `capabilities` section of their `agent.json` (or equivalent discovery document).

**Location:** `capabilities.extensions["https://a2a.dev/extensions/saga/v1"]`

**Schema:**

```json
{
  "type": "object",
  "required": ["roles"],
  "properties": {
    "roles": {
      "type": "array",
      "items": { "type": "string", "enum": ["orchestrator", "participant"] },
      "minItems": 1
    },
    "max_concurrent_sagas": { "type": "integer", "description": "Optional limit on concurrency" }
  }
}
```

_Example `agent.json` snippet:_

```json
{
  "capabilities": {
    "extensions": {
      "https://a2a.dev/extensions/saga/v1": {
        "roles": ["participant"],
        "max_concurrent_sagas": 50
      }
    }
  }
}
```

## 6. Protocol Surface

A2A-SAGA defines the following JSON-RPC methods:

1. `saga.start` (Orchestrator entry point)
2. `saga.step.execute` (Participant action)
3. `saga.step.verify` (Participant check)
4. `saga.step.compensate` (Participant undo)
5. `saga.abort` (Orchestrator cancellation)
6. `saga.status` (Observability)

### 6.1 Error Handling Strategy

Implementations MUST distinguish between **Protocol Errors** and **Application Failures**.

- **Protocol Errors:** Returned as JSON-RPC Error objects (non-200 semantic).
  - `-32600`: Invalid Request (e.g., missing `idempotency_key`).
  - `-32602`: Invalid Params (e.g., schema violation).
- **Application Failures:** Returned as a valid JSON-RPC `result` object with `status: "failed"` or `status: "unknown"`.
  - This allows the orchestrator to inspect the `failure` payload (reason, criticality) and decide on retry vs. compensation.

## 7. Parallel Group Semantics (Normative)

### 7.1 Grouping

Steps MAY include a `group` identifier. Steps with the same group MAY be executed concurrently.

### 7.2 Execution Ordering

Let groups be ordered by first appearance in the saga’s `steps` array: `G1, G2, …, Gn`.

An orchestrator that supports parallel groups (conformance O1) MUST NOT begin executing any step in `Gi+1` until all steps in `Gi` have reached a **terminal decision**.

A **terminal decision** is one of:

- `succeeded`
- `failed`
- `unknown` (only after verification has confirmed the outcome is truly unresolvable or negative).


### 7.3 Compensation Ordering

When compensation is initiated:

1. Only steps known to have applied effects (i.e., `succeeded` or `unknown` verified as applied) are eligible for compensation.
2. Compensation MUST proceed in reverse group order: `Gn … G1`.
3. Within a group, compensations MAY be run concurrently.

## 8. Failure Semantics (Normative)

### 8.1 Failure Classification (On Wire)

If a step result is not successful (`failed`, `unknown`, or `pending_approval`), participants MUST include a `failure` object containing `failure_class` and `reason`.

`failure_class` MUST be one of:

- `transient`: (e.g., network timeout) - Retry likely to succeed.
- `deterministic`: (e.g., validation error) - Retry will fail.
- `policy`: (e.g., quota exceeded) - Retry depends on policy reset.
- `semantic`: (e.g., item out of stock) - Logic failure.
- `unknown`: Root cause undetermined.

### 8.2 Unknown Outcomes & Verification

If a participant returns `status = "unknown"`:

1. If the step definition includes a `verify` action AND the participant supports `saga.step.verify`:
- The orchestrator MUST invoke `saga.step.verify` before deciding to retry or compensate.
2. If verification confirms the action succeeded, the step is treated as `succeeded`.
3. If verification confirms the action did _not_ happen, the orchestrator MAY retry (if safe) or fail.
4. If verification returns `status = "not_supported"`, the orchestrator MUST treat the step as having an **unknown** outcome and decide by policy whether to retry `execute`, fail the saga, or compensate.

## 9. Idempotency (Normative)

### 9.1 Required Keys

All `saga.step.execute` and `saga.step.compensate` requests MUST include `idempotency_key`.

### 9.2 Participant Obligations

Participants MUST ensure that repeated calls with the same `idempotency_key`:

1. **Safety:** MUST NOT apply additional side effects.
2. **Consistency:** MUST return a **consistent** `status` and `evidence` structure that is stable across replays.

## 10. Conformance

### 10.1 Participant Conformance

- **P-Min:** Implements `saga.step.execute` with strict idempotency.
- **P0:** P-Min + `saga.step.compensate`.
- **P1 (Recommended):** P0 + `saga.step.verify`.

### 10.2 Orchestrator Conformance

- **O0:** Serial execution, basic compensation on failure.
- **O1:** Supports parallel groups (Section 7) and verification logic (Section 8.2).

## Appendix A — Normative JSON Schemas

**Notes:** Schemas are JSON Schema Draft 2020-12.

## A.1 `common` schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "A2A-SAGA Common Types",
  "type": "object",
  "$defs": {
    "SagaId": {
      "type": "string",
      "minLength": 1,
      "maxLength": 256,
      "pattern": "^[A-Za-z0-9._:-]+$"
    },
    "StepId": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "pattern": "^[A-Za-z0-9._:-]+$"
    },
    "IdempotencyKey": {
      "type": "string",
      "minLength": 8,
      "maxLength": 512
    },
    "FailureClass": {
      "type": "string",
      "enum": ["transient", "deterministic", "policy", "semantic", "unknown"]
    },
    "StepStatus": {
      "type": "string",
      "enum": ["succeeded", "failed", "unknown", "pending_approval"]
    },
    "VerifyStatus": {
      "type": "string",
      "enum": ["verified", "not_verified", "unknown", "not_supported"]
    },
    "CompensateStatus": {
      "type": "string",
      "enum": ["compensated", "failed", "unknown", "pending_approval", "not_supported"]
    },
    "Reversibility": {
      "type": "string",
      "enum": ["full", "partial", "none"]
    },
    "Criticality": {
      "type": "string",
      "enum": ["low", "medium", "high"]
    },
    "ActionRef": {
      "type": "object",
      "additionalProperties": false,
      "required": ["action", "args"],
      "properties": {
        "action": { "type": "string", "minLength": 1, "maxLength": 256 },
        "args": { "type": "object" }
      }
    },
    "ExecuteSpec": {
      "allOf": [
        { "$ref": "#/$defs/ActionRef" },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["idempotency_key"],
          "properties": {
            "action": { "type": "string" },
            "args": { "type": "object" },
            "idempotency_key": { "$ref": "#/$defs/IdempotencyKey" }
          }
        }
      ]
    },
    "CompensateSpec": {
      "allOf": [
        { "$ref": "#/$defs/ActionRef" },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["idempotency_key"],
          "properties": {
            "action": { "type": "string" },
            "args": { "type": "object" },
            "idempotency_key": { "$ref": "#/$defs/IdempotencyKey" }
          }
        }
      ]
    },
    "VerifySpec": { "$ref": "#/$defs/ActionRef" },
    "FailureInfo": {
      "type": "object",
      "additionalProperties": false,
      "required": ["failure_class", "reason"],
      "properties": {
        "failure_class": { "$ref": "#/$defs/FailureClass" },
        "reason": { "type": "string", "minLength": 1, "maxLength": 4096 },
        "retry_after_ms": { "type": "integer", "minimum": 0, "maximum": 86400000 },
        "details": { "type": "object" }
      }
    },
    "Evidence": {
      "type": "object",
      "description": "Opaque evidence payload; may include signed receipts, hashes, timestamps.",
      "additionalProperties": true
    },
    "StepDefinition": {
      "type": "object",
      "additionalProperties": false,
      "required": ["step_id", "participant", "execute", "reversibility", "criticality"],
      "properties": {
        "step_id": { "$ref": "#/$defs/StepId" },
        "participant": {
          "type": "string",
          "description": "Participant identifier or URL.",
          "minLength": 1,
          "maxLength": 2048
        },
        "execute": { "$ref": "#/$defs/ExecuteSpec" },
        "verify": { "$ref": "#/$defs/VerifySpec" },
        "compensate": { "$ref": "#/$defs/CompensateSpec" },
        "reversibility": { "$ref": "#/$defs/Reversibility" },
        "criticality": { "$ref": "#/$defs/Criticality" },
        "group": {
          "type": "string",
          "description": "Optional parallel group identifier.",
          "minLength": 1,
          "maxLength": 128,
          "pattern": "^[A-Za-z0-9._:-]+$"
        },
        "metadata": { "type": "object" }
      }
    }
  }
}
```

## A.2 `saga.start` schemas

### A.2.1 `saga.start.params`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.start params",
  "type": "object",
  "additionalProperties": false,
  "required": ["saga_id", "goal", "steps"],
  "properties": {
    "saga_id": { "$ref": "#/$defs/SagaId" },
    "goal": { "type": "string", "minLength": 1, "maxLength": 4096 },
    "steps": {
      "type": "array",
      "items": { "$ref": "#/$defs/StepDefinition" },
      "minItems": 1
    },
    "policy": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "require_approval_for": {
          "type": "array",
          "items": { "$ref": "#/$defs/Criticality" }
        },
        "max_irreversible_steps": { "type": "integer", "minimum": 0, "maximum": 1000 }
      }
    },
    "metadata": { "type": "object" }
  },
  "$defs": {}
}
```

### A.2.2 `saga.start.result`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.start result",
  "type": "object",
  "additionalProperties": false,
  "required": ["status", "state"],
  "properties": {
    "status": { "type": "string", "enum": ["accepted", "rejected"] },
    "state": {
      "type": "string",
      "enum": ["saga_running", "saga_waiting", "saga_failed", "saga_compensating", "saga_compensated", "saga_completed"]
    },
    "failure": { "$ref": "#/$defs/FailureInfo" }
  },
  "$defs": {}
}
```

## A.3 `saga.step.execute` schemas

### A.3.1 `saga.step.execute.params`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.execute params",
  "type": "object",
  "additionalProperties": false,
  "required": ["saga_id", "step_id", "execute"],
  "properties": {
    "saga_id": { "$ref": "#/$defs/SagaId" },
    "step_id": { "$ref": "#/$defs/StepId" },
    "execute": { "$ref": "#/$defs/ExecuteSpec" },
    "metadata": { "type": "object" }
  },
  "$defs": {}
}
```

### A.3.2 `saga.step.execute.result`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.execute result",
  "type": "object",
  "additionalProperties": false,
  "required": ["status"],
  "properties": {
    "status": { "$ref": "#/$defs/StepStatus" },
    "evidence": { "$ref": "#/$defs/Evidence" },
    "failure": { "$ref": "#/$defs/FailureInfo" }
  },
  "allOf": [
    {
      "if": { "properties": { "status": { "const": "succeeded" } } },
      "then": { "required": ["evidence"] }
    },
    {
      "if": { "properties": { "status": { "enum": ["failed", "unknown", "pending_approval"] } } },
      "then": { "required": ["failure"] }
    }
  ],
  "$defs": {}
}
```

## A.4 `saga.step.verify` schemas

### A.4.1 `saga.step.verify.params`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.verify params",
  "type": "object",
  "additionalProperties": false,
  "required": ["saga_id", "step_id", "verify"],
  "properties": {
    "saga_id": { "$ref": "#/$defs/SagaId" },
    "step_id": { "$ref": "#/$defs/StepId" },
    "verify": { "$ref": "#/$defs/VerifySpec" },
    "metadata": { "type": "object" }
  },
  "$defs": {}
}
```

### A.4.2 `saga.step.verify.result`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.verify result",
  "type": "object",
  "additionalProperties": false,
  "required": ["status"],
  "properties": {
    "status": { "$ref": "#/$defs/VerifyStatus" },
    "details": { "type": "object" },
    "failure": { "$ref": "#/$defs/FailureInfo" }
  },
  "$defs": {}
}
```

## A.5 `saga.step.compensate` schemas

### A.5.1 `saga.step.compensate.params`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.compensate params",
  "type": "object",
  "additionalProperties": false,
  "required": ["saga_id", "step_id", "compensate"],
  "properties": {
    "saga_id": { "$ref": "#/$defs/SagaId" },
    "step_id": { "$ref": "#/$defs/StepId" },
    "compensate": { "$ref": "#/$defs/CompensateSpec" },
    "metadata": { "type": "object" }
  },
  "$defs": {}
}
```

### A.5.2 `saga.step.compensate.result`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "saga.step.compensate result",
  "type": "object",
  "additionalProperties": false,
  "required": ["status"],
  "properties": {
    "status": { "$ref": "#/$defs/CompensateStatus" },
    "evidence": { "$ref": "#/$defs/Evidence" },
    "failure": { "$ref": "#/$defs/FailureInfo" }
  },
  "allOf": [
    {
      "if": { "properties": { "status": { "const": "compensated" } } },
      "then": { "required": ["evidence"] }
    },
    {
      "if": { "properties": { "status": { "enum": ["failed", "unknown", "pending_approval"] } } },
      "then": { "required": ["failure"] }
    }
  ],
  "$defs": {}
}
```

## Appendix B — Normative Test Vectors

## B.1 Test Vector Rules (Normative)

- **Normativity:** Implementations claiming conformance MUST be able to process these message sequences and produce results that conform to the schemas and match the expected status.
- **Evidence:** Evidence values (IDs, timestamps) MAY differ unless the vector explicitly requires stability (see B.3).

## B.2 Test Vector Set A — Parallel Groups + Recovery

### B.2.1 Scenario

Goal: “Onboard customer c123” with parallel execution, failure, and compensation.

1. **Group G1:** `reserve_username` (Identity), `create_customer` (CRM) -> Both Succeed.
2. **Group G2:** `provision_workspace` -> Returns `unknown`.
3. **Action:** Orchestrator verifies `provision_workspace` -> `not_verified` (Effect did not happen).
4. **Action:** Orchestrator retries `provision_workspace` -> Fails deterministically.
5. **Recovery:** Orchestrator aborts. Compensates G1 in parallel.

### B.2.2 `saga.start`

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-1",
  "method": "saga.start",
  "params": {
    "saga_id": "tvA-saga-001",
    "goal": "Onboard customer c123",
    "steps": [
      {
        "step_id": "reserve_username",
        "group": "g1",
        "participant": "a2a://agent/identity",
        "execute": {
          "action": "reserve_username",
          "args": { "customer_id": "c123", "username": "acme" },
          "idempotency_key": "tvA-saga-001:reserve_username:exec"
        },
        "compensate": {
          "action": "release_username",
          "args": { "username": "acme" },
          "idempotency_key": "tvA-saga-001:reserve_username:comp"
        },
        "reversibility": "full",
        "criticality": "medium"
      },
      {
        "step_id": "create_customer_record",
        "group": "g1",
        "participant": "a2a://agent/crm",
        "execute": {
          "action": "create_customer",
          "args": { "customer_id": "c123", "name": "ACME" },
          "idempotency_key": "tvA-saga-001:create_customer_record:exec"
        },
        "compensate": {
          "action": "delete_customer",
          "args": { "customer_id": "c123" },
          "idempotency_key": "tvA-saga-001:create_customer_record:comp"
        },
        "reversibility": "full",
        "criticality": "high"
      },
      {
        "step_id": "provision_workspace",
        "group": "g2",
        "participant": "a2a://agent/provision",
        "execute": {
          "action": "provision_workspace",
          "args": { "customer_id": "c123", "plan": "pro" },
          "idempotency_key": "tvA-saga-001:provision_workspace:exec"
        },
        "verify": {
          "action": "get_workspace",
          "args": { "customer_id": "c123" }
        },
        "reversibility": "full",
        "criticality": "high"
      }
    ]
  }
}
```

**Result:** `{"status": "accepted", "state": "saga_running"}`

### B.2.3 Execute Group G1 (Parallel)

**Request (Identity):**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-2",
  "method": "saga.step.execute",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "reserve_username",
    "execute": { ... }
  }
}
```

**Result:** `{"status": "succeeded", "evidence": {"reservation_id": "resv-001"}}`

**Request (CRM):**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-3",
  "method": "saga.step.execute",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "create_customer_record",
    "execute": { ... }
  }
}
```

**Result:** `{"status": "succeeded", "evidence": {"customer_row_id": "crm-777"}}`

### B.2.4 Execute Group G2 (Unknown Outcome)

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-4",
  "method": "saga.step.execute",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "provision_workspace",
    "execute": { ... }
  }
}
```

**Result:**

```json
{
  "status": "unknown",
  "failure": {
    "failure_class": "unknown",
    "reason": "timeout after dispatch"
  }
}
```

### B.2.5 Verification

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-5",
  "method": "saga.step.verify",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "provision_workspace",
    "verify": { ... }
  }
}
```

**Result:**

```json
{
  "status": "not_verified",
  "details": { "workspace": null }
}
```

### B.2.6 Retry & Failure

Request: (Retry of tvA-4)

Result:

```json
{
  "status": "failed",
  "failure": {
    "failure_class": "deterministic",
    "reason": "Plan not available"
  }
}
```

### B.2.7 Abort & Compensation

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-7",
  "method": "saga.abort",
  "params": {
    "saga_id": "tvA-saga-001",
    "reason": "provision_workspace failed"
  }
}
```

**Result:** `{"status": "aborting", "state": "saga_compensating"}`

**Request (Compensate Identity):**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-8",
  "method": "saga.step.compensate",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "reserve_username",
    "compensate": { ... }
  }
}
```

**Result:** `{"status": "compensated", "evidence": {"released": true}}`

**Request (Compensate CRM):**

```json
{
  "jsonrpc": "2.0",
  "id": "tvA-9",
  "method": "saga.step.compensate",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "create_customer_record",
    "compensate": { ... }
  }
}
```

**Result:** `{"status": "compensated", "evidence": {"deleted": true}}`

## B.3 Test Vector Set B — Idempotent Replay

### B.3.1 Scenario

Replaying the same `idempotency_key` for execute MUST return consistent output.

**Request:** (Identical to tvA-2)

```json
{
  "jsonrpc": "2.0",
  "id": "tvB-1",
  "method": "saga.step.execute",
  "params": {
    "saga_id": "tvA-saga-001",
    "step_id": "reserve_username",
    "execute": {
      "action": "reserve_username",
      "args": { "customer_id": "c123", "username": "acme" },
      "idempotency_key": "tvA-saga-001:reserve_username:exec"
    }
  }
}
```

**Result:** (MUST match tvA-2)

```json
{
  "status": "succeeded",
  "evidence": { "reservation_id": "resv-001" }
}
```
