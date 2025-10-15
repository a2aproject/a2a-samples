import logging
from agp_protocol import AgentGatewayProtocol, AGPTable, CapabilityAnnouncement
from agp_protocol.agp_delegation_models import (
    DelegationRouter,
    DelegationIntent,
    SubIntent,
)
from typing import List


# Set logging level to INFO or WARNING to focus on routing output
logging.basicConfig(level=logging.WARNING)


def setup_enterprise_agp_table(gateway: AgentGatewayProtocol):
    """
    Simulates Capability Announcements from five specialized, multi-framework Squads.
    These announcements build the routing table used for PBR.
    """

    print("--- 1. Announcing Capabilities (Building AGP Routing Table) ---")

    # --- SQUAD 1: FINANCE (Google ADK) ---
    # High-Trust, Policy-Critical (Security Level 5)
    finance_announcement = CapabilityAnnouncement(
        capability="budget:authorize",
        version="1.0",
        cost=0.12,
        policy={"security_level": 5, "requires_role": "finance_admin", "geo": "US"},
    )
    gateway.announce_capability(
        finance_announcement, path="Finance_ADK/budget_gateway"
    )

    # --- SQUAD 2: ENGINEERING (LangChain) ---
    # Cost-Sensitive (Lowest cost, standard security)
    eng_announcement = CapabilityAnnouncement(
        capability="infra:provision",
        version="1.5",
        cost=0.04,  # Lowest cost option
        policy={"security_level": 3, "geo": "US"},
    )
    gateway.announce_capability(
        eng_announcement, path="Engineering_LC/provisioner_tool"
    )

    # --- SQUAD 3: HR (LangChain) ---
    # Strict Compliance (Requires PII handling, Security Level 4)
    hr_announcement = CapabilityAnnouncement(
        capability="onboarding:initiate",
        version="1.0",
        cost=0.15,
        policy={"security_level": 4, "requires_pii": True, "geo": "US"},
    )
    gateway.announce_capability(
        hr_announcement, path="HR_LC/onboarding_service"
    )

    # --- SQUAD 4: MARKETING (LangGraph) ---
    # Standard Content Task (High volume, low security)
    marketing_announcement = CapabilityAnnouncement(
        capability="content:draft",
        version="2.0",
        cost=0.08,
        policy={"security_level": 2, "geo": "US"},
    )
    gateway.announce_capability(
        marketing_announcement, path="Marketing_LG/content_tool"
    )

    # --- SQUAD 5: COMPLIANCE (Google ADK) ---
    # Zero-Trust/RBAC (Role-restricted, highest security level offered internally)
    compliance_announcement = CapabilityAnnouncement(
        capability="policy:audit",
        version="1.0",
        cost=0.20,
        policy={"security_level": 5, "requires_role": "exec", "geo": "US"},
    )
    gateway.announce_capability(
        compliance_announcement, path="Compliance_ADK/audit_service"
    )

    # --- Announcement 6: CHEAP EXTERNAL VENDOR ---
    # Non-compliant competitor—used to verify PBR filtering
    cheap_external_announcement = CapabilityAnnouncement(
        capability="infra:provision",
        version="1.0",
        cost=0.03,  # CHEAPER than Engineering, but fails security
        policy={"security_level": 1, "geo": "US"},
    )
    gateway.announce_capability(
        cheap_external_announcement, path="External_Vendor/vm_tool"
    )


def run_enterprise_simulation():
    """
    Executes the simulation of an Executive Project Launch delegation
    through the Central AGP Gateway.
    """
    # Initialize the AGP Gateway
    agp_table = AGPTable()
    central_gateway = AgentGatewayProtocol(
        squad_name="Central_AGP_Router", agp_table=agp_table
    )

    # Build the routing table
    setup_enterprise_agp_table(central_gateway)

    print("\n--- 2. Building Delegation Task (HR Initiates Project Setup) ---")

    # Define the Complex Delegation Task (Executive Project Launch)
    project_delegation_intent = DelegationIntent(
        meta_task="Executive Project Launch: Q4 Strategy Initiative",
        origin_squad="HR_Squad_Orchestrator",
        sub_intents=[
            # TASK 1: Finance Authorization (L5 Security Required)
            SubIntent(
                target_capability="budget:authorize",
                payload={"project_id": "Q4-STRAT", "amount": 50000},
                policy_constraints={"security_level": 5, "requires_role": "finance_admin"},
            ),
            # TASK 2: Infrastructure Provisioning (Cost Sensitive, L3 Security Required)
            SubIntent(
                target_capability="infra:provision",
                payload={"vm_type": "standard_compute"},
                policy_constraints={"security_level": 3, "cost_max": 0.05}, 
            ),
            # TASK 3: Personnel Onboarding (PII Mandatory)
            SubIntent(
                target_capability="onboarding:initiate",
                payload={"role": "Lead Architect", "candidate_name": "Jane Doe"},
                policy_constraints={"requires_pii": True},
            ),
            # TASK 4: Compliance Audit Check (RBAC Restriction)
            SubIntent(
                target_capability="policy:audit",
                payload={"report": "Q4"},
                policy_constraints={"requires_role": "exec"},
            ),
            # TASK 5: Marketing Content Draft (Low Security, High Volume)
            SubIntent(
                target_capability="content:draft",
                payload={"topic": "Strategy Launch PR"},
                policy_constraints={"security_level": 2},
            ),
        ],
    )

    # Initialize the Delegation Router
    router = DelegationRouter(central_gateway=central_gateway)

    print("\n--- 3. Executing Delegation and Policy Routing ---")
    print("Routing Agent: Central_AGP_Router")

    # Execute the decomposition and routing
    final_status = router.route_delegation_intent(project_delegation_intent)

    print("\n--- 4. Final Aggregation Status ---")
    for task, status in final_status.items():
        print(f"Task '{task}': {status}")


if __name__ == "__main__":
    run_enterprise_simulation()