# Cross Framework Agent Simulation: Enterprise Delegation 

TL;DR: This document specifies a comprehensive, cross-framework agentic simulation built upon the Agent Gateway Protocol (AGP), designed to model distributed enterprise squads. This simulation, spanning five distinct departments—Finance, Engineering, Marketing, HR, and Compliance—and three diverse technology stacks, will robustly demonstrate the AGP's efficacy in cross-framework enterprise integration and, critically, its proficiency in managing security and trust boundaries.

* URI: [https://github.com/a2aproject/a2a-samples/blob/main/extensions/agp/sim/enterprise-v1](https://github.com/a2aproject/a2a-samples/blob/main/extensions/agp/sim/enterprise-v1)   
* Goal: Simulate cross-framework (ADK, LangChain, LangGraph) delegation of a complex "Executive Project Launch" task via the [AGP PBR layer](https://github.com/a2aproject/a2a-samples/blob/main/extensions/agp/), emphasizing security and compliance boundaries. 

**Framework Agnosticism:** The core role of the AGP is to act as a secure, framework-agnostic routing layer. The Gateway's job is to route based purely on the Policy (e.g., `security_level`, `requires_pii`) and the Capability (e.g., `infra:provision and infra:performance`), without needing to know if the destination agent is written in ADK or LangChain or another Framework - gulli@google.com

## 1\. Domain and Technology Architecture

The simulation comprises five specialized Autonomous Squads (ASqs) across a corporate hierarchy, with Gateways connecting the domains based on specialized Agent Capabilities.

Crucially, each ASq represents a significant internal department (a hierarchical domain) operating with internal teams ranging from 10 to 100s or more of specialized, fine-tuned agents. The Gateway Agent abstracts this internal complexity.

| Domain (Squad) | Primary Role | Agent Framework | Security & Trust Focus | Primary Capability |
| :---- | :---- | :---- | :---- | :---- |
| Finance | Budgeting & Compliance | Google ADK | Policy-Critical / High-Trust | budget:authorize |
| Engineering | Resource Provisioning | LangChain | Cost-Sensitive / Standard | infra:provision |
| HR | Personnel & Onboarding | LangChain | PII Segregation / Compliance | onboarding:initiate |
| Marketing | Content Generation | LangGraph | Creative / High-Velocity | content:draft |
| Compliance | Audit & Policy Check | Google ADK | Zero-Trust / Role-Based Access | policy:audit |

## 2\. Core Intent: Delegation Payload

For this complex simulation, the orchestrator will send a single Delegation Intent that the central AGP Gateway must decompose and route to multiple specialized Squads.

### DelegationIntent Object Schema

This object will be routed to the central AGP Gateway.

| Field | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| meta\_task | string | Yes | High-level goal (e.g., "Setup Project Alpha"). |
| sub\_intents | array\<object\> | Yes | List of atomic tasks to be decomposed and routed. |
| origin\_squad | string | Yes | The squad initiating the request (used for reporting final status). |

### SubIntent Object Schema

| Field | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| target\_capability | string | Yes | The specific AGP capability to route (e.g., infra:provision). |
| payload | object | Yes | Data specific to the sub-intent (e.g., budget amount, VM type). |
| policy\_constraints | object | No | Specific security/geo constraints for this individual sub-task. |

## 3\. Delegation Flow

1. HR Delegation: The HR Agent generates a single DelegationIntent with five SubIntents corresponding to the tasks defined in Section 4.
2. AGP Routing: The Central Gateway receives the DelegationIntent. It processes each SubIntent against its AGP Routing Table, applying Policy-Based Routing:  
   * Finance and Compliance tasks require high security/role checks.  
   * Engineering tasks require cost optimization.  
3. Cross-Framework Execution:  
   * budget:authorize is routed to the Google ADK Squad (Finance).  
   * infra:provision is routed to the LangChain Squad (Engineering).  
4. Fulfillment: Each specialized Squad fulfills its task using its own framework/tools.  
5. Aggregation: The Central Gateway aggregates the fulfillment results to confirm the project setup is complete.

## 4\. Specific AGP Routing Rules (PBR Verification)

The simulation must verify the following Policy-Based Routing decisions:

| Scenario | Intent Capability | Intent Constraint | Compliant Route | Principle Verified |
| :---- | :---- | :---- | :---- | :---- |
| Finance (Budget) | budget:authorize | security\_level: 5 | Google ADK Squad (Finance) | Sufficiency: Ensures the high-level financial task is handled by the secure L5 squad. |
| Compliance (Audit) | policy:audit | requires\_role: exec | Google ADK Squad (Compliance) | Role-Based Access Control (RBAC): Verifies that the delegating agent has the authority (exec role) to initiate a sensitive audit check. |
| Engineering (Infra) | infra:provision | cost\_max: 0.05 | LangChain Squad (Engineering) | Economic: Ensures the routing selects the cheapest route under a specific constraint. |
| HR (PII) | onboarding:initiate | requires\_pii: True | LangChain Squad (HR) | Strict Compliance: Ensures PII tasks are routed *only* to the designated squad that explicitly declares PII handling capability. |

## 5\. Conclusion and Next Steps

The proposed enterprise simulation represents the necessary evolution of agent architectures for industrial scale. By establishing a robust hierarchical architecture that manages tasks across five departments and three distinct technology stacks, the Agent Gateway Protocol (AGP) proves its capability to enforce Zero-Trust principles.

The AGP acts as the crucial policy backbone, ensuring that all cross-domain tasks—from cost-sensitive provisioning to role-restricted audits—are routed securely and compliantly. The successful implementation of this simulation validates the AGP as a ready framework for trustworthy, cross-framework agent collaboration.

# Appendix

## AGP's Relationship with A2A

The AGP is designed not to replace A2A but to serve as a **critical enhancement layer**. Without the basic A2A framework, AGP cannot function.

## 1\. The A2A Foundation (The "How")

The AGP relies on the core capabilities of the A2A Protocol for all external communication:

* **Communication Channel:** The final action taken by the Gateway Router, when it finds the best route (e.g., `Finance_ADK/budget_gateway`), is to pass the **Intent** payload to the correct Agent Squad. That transfer *must* happen over the underlying **A2A communication channels** (like JSON-RPC over HTTP, which A2A standardizes).  
* **Discovery:** A2A's native **Agent Card** mechanism is used by Squad Gateways to declare their role and supported AGP version to the network.  
* **Message Format:** The AGP **Intent Payload** is structured to be compatible with A2A's core message exchange capabilities, often embedded within an A2A message's data payload.

### 2\. The AGP Enhancement (The "Why")

The AGP layer handles the **routing decision** that A2A leaves undefined.

* A standard A2A client only asks: "Do you offer this capability?"  
* An AGP client (the Gateway Router) asks: "Which compliant agent, out of the five available, is the cheapest and meets Security Level 5?"

The AGP introduces the **hierarchical logic** (Policy-Based Routing, Cost Selection) and the specific **Delegation Intents** to the A2A framework, making it suitable for cross-framework enterprise deployments.

In summary, AGP provides the intelligence and routing policy, while A2A provides the reliable, underlying communication transport layer. Your simulation verifies that this intelligent routing layer works.

## Test phase

(base) gulli-mac:agp gulli$ poetry run pytest tests/simulation/enterprise/test_enterprise_sim.py
===================================================================== test session starts ======================================================================
platform darwin -- Python 3.12.8, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/gulli/code/OCTO/ag/a2a-samples/extensions/agp
configfile: pyproject.toml
collected 5 items                                                                                                                                              

tests/simulation/enterprise/test_enterprise_sim.py .....                                                                                                 [100%]

====================================================================== 5 passed in 0.08s =======================================================================
(base) gulli-mac:agp gulli$ poetry run pytest tests/
simulation/  test_agp.py  
(base) gulli-mac:agp gulli$ poetry run pytest tests/test_agp.py 
===================================================================== test session starts ======================================================================
platform darwin -- Python 3.12.8, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/gulli/code/OCTO/ag/a2a-samples/extensions/agp
configfile: pyproject.toml
collected 19 items                                                                                                                                             

tests/test_agp.py ...................                                                                                                                    [100%]

====================================================================== 19 passed in 0.06s ======================================================================
(base) gulli-mac:agp gulli$ 
