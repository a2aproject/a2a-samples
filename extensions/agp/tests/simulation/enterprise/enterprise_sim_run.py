import logging

from agp_protocol import AGPTable, AgentGatewayProtocol, CapabilityAnnouncement
from agp_protocol.agp_delegation_models import (
    DelegationIntent,
    DelegationRouter,
    SubIntent,
)


# Set logging level to WARNING so only our custom routing failures are visible
logging.basicConfig(level=logging.WARNING)


# --- DATA DEFINITION: Centralized Capabilities List ---
# This list defines all squads and their announced policies and costs in a data-driven structure.
ENTERPRISE_CAPABILITIES = [
    # 1. FINANCE (Policy-Critical / High-Trust / Google ADK)
    {
        'capability': 'budget:authorize',
        'version': '1.0',
        'cost': 0.12,
        'path': 'Finance_ADK/budget_gateway',
        'policy': {
            'security_level': 5,
            'requires_role': 'finance_admin',
            'geo': 'US',
        },
    },
    # 2. ENGINEERING (Cost-Sensitive / LangChain)
    {
        'capability': 'infra:provision',
        'version': '1.5',
        'cost': 0.04,
        'path': 'Engineering_LC/provisioner_tool',
        'policy': {'security_level': 3, 'geo': 'US'},
    },
    # 3. HR (Strict Compliance / PII / LangChain)
    {
        'capability': 'onboarding:initiate',
        'version': '1.0',
        'cost': 0.15,
        'path': 'HR_LC/onboarding_service',
        'policy': {'security_level': 4, 'requires_pii': True, 'geo': 'US'},
    },
    # 4. MARKETING (High Volume / Low Security / LangGraph)
    {
        'capability': 'content:draft',
        'version': '2.0',
        'cost': 0.08,
        'path': 'Marketing_LG/content_tool',
        'policy': {'security_level': 2, 'geo': 'US'},
    },
    # 5. COMPLIANCE (Zero-Trust/RBAC / Google ADK)
    {
        'capability': 'policy:audit',
        'version': '1.0',
        'cost': 0.20,
        'path': 'Compliance_ADK/audit_service',
        'policy': {'security_level': 5, 'requires_role': 'exec', 'geo': 'US'},
    },
    # 6. CHEAP EXTERNAL VENDOR (Non-compliant competitor for 'infra:provision')
    {
        'capability': 'infra:provision',
        'version': '1.0',
        'cost': 0.03,  # CHEAPER than Engineering, but fails security check
        'path': 'External_Vendor/vm_tool',
        'policy': {'security_level': 1, 'geo': 'US'},
    },
]


def setup_enterprise_agp_table(gateway: AgentGatewayProtocol):
    """Simulates Capability Announcements from five specialized, multi-framework Squads.
    Refactored to be data-driven.
    """
    # CORRECTED: Replaced print() with logging.info()
    logging.info(
        '--- 1. Announcing Capabilities (Building AGP Routing Table) ---'
    )

    for item in ENTERPRISE_CAPABILITIES:
        announcement = CapabilityAnnouncement(
            capability=item['capability'],
            version=item['version'],
            cost=item['cost'],
            policy=item['policy'],
        )
        gateway.announce_capability(announcement, path=item['path'])


def run_enterprise_simulation():
    """Executes the simulation of an Executive Project Launch delegation
    through the Central AGP Gateway.
    """
    # Initialize the AGP Gateway
    agp_table = AGPTable()
    central_gateway = AgentGatewayProtocol(
        squad_name='Central_AGP_Router', agp_table=agp_table
    )

    # Build the routing table
    setup_enterprise_agp_table(central_gateway)

    logging.info(
        '\n--- 2. Building Delegation Task (HR Initiates Project Setup) ---'
    )

    # Define the Complex Delegation Task (Executive Project Launch)
    project_delegation_intent = DelegationIntent(
        meta_task='Executive Project Launch: Q4 Strategy Initiative',
        origin_squad='HR_Squad_Orchestrator',
        sub_intents=[
            # TASK 1: Finance Authorization (L5 Security Required)
            SubIntent(
                target_capability='budget:authorize',
                payload={'project_id': 'Q4-STRAT', 'amount': 50000},
                policy_constraints={
                    'security_level': 5,
                    'requires_role': 'finance_admin',
                },
            ),
            # TASK 2: Infrastructure Provisioning (Cost Sensitive, L3 Security Required)
            SubIntent(
                target_capability='infra:provision',
                payload={'vm_type': 'standard_compute'},
                policy_constraints={'security_level': 3, 'cost_max': 0.05},
            ),
            # TASK 3: Personnel Onboarding (PII Mandatory)
            SubIntent(
                target_capability='onboarding:initiate',
                payload={
                    'role': 'Lead Architect',
                    'candidate_name': 'Jane Doe',
                },
                policy_constraints={'requires_pii': True},
            ),
            # TASK 4: Compliance Audit Check (RBAC Restriction)
            SubIntent(
                target_capability='policy:audit',
                payload={'report': 'Q4'},
                policy_constraints={'requires_role': 'exec'},
            ),
            # TASK 5: Marketing Content Draft (Low Security, High Volume)
            SubIntent(
                target_capability='content:draft',
                payload={'topic': 'Strategy Launch PR'},
                policy_constraints={'security_level': 2},
            ),
        ],
    )

    # Initialize the Delegation Router
    router = DelegationRouter(central_gateway=central_gateway)

    logging.info('\n--- 3. Executing Delegation and Policy Routing ---')
    logging.info('Routing Agent: Central_AGP_Router')

    # Execute the decomposition and routing
    final_status = router.route_delegation_intent(project_delegation_intent)

    logging.info('\n--- 4. Final Aggregation Status ---')
    for task, status in final_status.items():
        logging.info(f"Task '{task}': {status}")


if __name__ == '__main__':
    run_enterprise_simulation()

if __name__ == '__main__':
    run_enterprise_simulation()
