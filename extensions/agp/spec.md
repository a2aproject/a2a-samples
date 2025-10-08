# Agent Gateway Protocol (AGP) Specification (V1)

* **URI:** `https://github.com/a2aproject/a2a-samples/tree/main/extensions/agp`

* **Type:** Core Protocol Layer / Routing Extension

* **Version:** 1.0.0

## Abstract

The Agent Gateway Protocol (AGP) proposes a hierarchical architecture for distributed AI systems, **enhancing the capabilities** of the flat A2A mesh by introducing a structure of interconnected Autonomous Squads (ASq). AGP routes **Intent** payloads based on declared **Capabilities**, mirroring the Border Gateway Protocol (BGP) for Internet scalability and policy enforcement. This structure divides agents into **hierarchical domains**, with each domain focusing on specific Agent Capabilities that reflect enterprise organizational needs (e.g., Finance, Engineering, HR, BUs, and so on) - gulli@google.com 

## 1. Data Structure: Capability Announcement

This payload is used by a Squad Gateway Agent to announce the services its squad can fulfill to its peers (other squads).

### CapabilityAnnouncement Object Schema

| Field | Type | Required | Description |
 | ----- | ----- | ----- | ----- |
| `capability` | string | Yes | The function or skill provided (e.g., `financial_analysis:quarterly`). |
| `version` | string | Yes | Version of the capability schema/interface (e.g., `1.5`). |
| `cost` | number | No | Estimated cost metric (e.g., `0.05` USD, or token count). |
| `policy` | object | Yes | Key-value pairs defining required policies (e.g., `requires_pii:true`, `security_level:5`). |

### Example Announcement Payload

```json
{
  "capability": "financial_analysis:quarterly",
  "version": "1.5",
  "cost": 0.05,
  "policy": {
    "requires_auth": "level_3"
  }
}
```

## 2. Data Structure: Intent Payload

This payload defines the *what* (the goal) and *constraints* (metadata), replacing a standard request.

### Intent Object Schema

| Field | Type | Required | Description |
 | ----- | ----- | ----- | ----- |
| `target_capability` | string | Yes | The capability the Intent seeks to fulfill. |
| `payload` | object | Yes | The core data arguments required for the task. |
| `policy_constraints` | object | No | Client-defined constraints that must be matched against the announced `policy` during routing. |

### Example Intent Payload

```json
{
  "target_capability": "billing:invoice:generate",
  "payload": {
    "customer_id": 123,
    "amount": 99.99
  },
  "policy_constraints": {
    "requires_pii": true
  }
}
```

## 3. Core Routing and Table Structures

The protocol relies on the Gateway Agent maintaining an **AGP Table** (a routing table) built from Capability Announcements. This section defines the core structures used internally by the Gateway Agent.

### A. RouteEntry Object Schema

| Field | Type | Required | Description |
 | ----- | ----- | ----- | ----- |
| `path` | string | Yes | The destination Squad/API path (e.g., `Squad_Finance/gateway`). |
| `cost` | number | Yes | The cost metric for this route (used for lowest-cost selection). |
| `policy` | object | Yes | Policies of the destination, used for matching Intent constraints. |

### B. AGPTable Object

The AGPTable maps a `capability` key to a list of potential `RouteEntry` objects.

## 4. Agent Declaration and Role

To participate in the AGP hierarchy, an A2A agent **MUST** declare its role as a Gateway and the supported AGP version within its Agent Card, using the A2A extension mechanism.

### AgentCard AGP Declaration

This declaration is placed within the `extensions` array of the Agent Card's `AgentCapabilities`.

```json
{
  "uri": "https://github.com/a2aproject/a2a-samples/tree/main/extensions/agp",
  "params": {
    "agent_role": "gateway",
    "supported_agp_versions": ["1.0"]
  }
}
```

## 5. Extension Error Reference

When a Gateway Agent attempts to route an Intent but fails due to policy or availability issues, it **MUST** return a JSON-RPC error with specific AGP-defined codes.

| Code | Name | Description | Routing Consequence |
 | ----- | ----- | ----- | ----- |
| **-32200** | `AGP_ROUTE_NOT_FOUND` | No agent or squad has announced the requested `target_capability`. | Intent cannot be routed; returned to sender. |
| **-32201** | `AGP_POLICY_VIOLATION` | Routes were found, but none satisfied the constraints in the Intent's `metadata` (e.g., no squad accepts PII data). | Intent cannot be routed safely; returned to sender. |
| **-32202** | `AGP_TABLE_STALE` | The Agent Gateway's routing table is outdated and needs a refresh via a standard AGP refresh mechanism. | Gateway attempts refresh before re-routing, or returns error. |

## 6. Conclusion

The Agent Gateway Protocol (AGP) offers a powerful and necessary enhancement layer over the foundational A2A structure. By implementing Policy-Based Routing, AGP ensures that distributed AI systems are not only efficient and financially optimized but also secure and policy-compliant—a critical step toward trustworthy, industrial-scale multi-agent collaboration.
