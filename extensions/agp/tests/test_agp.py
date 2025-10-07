import pytest

from agp_protocol import (
    AGPTable,
    AgentGatewayProtocol,
    CapabilityAnnouncement,
    IntentPayload,
    RouteEntry,
)


# --- Fixtures for Routing Table Setup ---


@pytest.fixture
def all_available_routes() -> list[RouteEntry]:
    """Defines a list of heterogeneous routes covering all capabilities needed for testing."""
    return [
        # 1. Base License/Legal Route (Security Level 3, Geo US)
        RouteEntry(
            path='Squad_Legal/licensing_api',
            cost=0.20,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 2. Secure/PII Route (Security Level 5, PII Handling True)
        RouteEntry(
            path='Squad_Finance/payroll_service',
            cost=0.10,
            # Policy explicitly supports PII handling and higher security
            policy={'security_level': 5, 'requires_pii': True, 'geo': 'US'},
        ),
        # 3. External Route (Cheapest, but low security/no PII)
        RouteEntry(
            path='Vendor_EU/proxy_gateway',
            cost=0.05,
            policy={'security_level': 1, 'geo': 'EU'},
        ),
        # 4. Hardware Provisioning Route (Engineering)
        RouteEntry(
            path='Squad_Engineering/hardware_tool',
            cost=0.08,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 5. NDA Contract Generation Route (Legal)
        RouteEntry(
            path='Squad_Legal/contracts_tool',
            cost=0.15,
            policy={'security_level': 3, 'geo': 'US'},
        ),
    ]


@pytest.fixture
def populated_agp_table(all_available_routes) -> AGPTable:
    """Creates an AGPTable populated with routes for all test capabilities."""
    table = AGPTable()

    # Routes for Core Routing Tests (Tests 1-4 use 'procure:license')
    table.routes['procure:license'] = [
        all_available_routes[0],
        all_available_routes[1],
        all_available_routes[2],
    ]

    # Routes for Decomposition Test (Test 6)
    table.routes['provision:hardware'] = [all_available_routes[3]]
    table.routes['provision:payroll'] = [
        all_available_routes[1]
    ]  # Secure route for payroll
    table.routes['contract:nda:generate'] = [all_available_routes[4]]

    return table


@pytest.fixture
def gateway(populated_agp_table) -> AgentGatewayProtocol:
    """Provides a configured Gateway Agent instance for testing."""
    return AgentGatewayProtocol(
        squad_name='Test_Gateway', agp_table=populated_agp_table
    )


# --- Test Scenarios ---


def test_01_lowest_cost_compliant_route_with_sufficiency(
    gateway: AgentGatewayProtocol,
):
    """
    Verifies routing selects the lowest cost COMPLIANT route, checking for sufficiency (>=).
    Constraint: security_level: 3, geo: US. Route 2 (Cost 0.10, Level 5) is compliant AND cheaper than Route 1 (Cost 0.20, Level 3).
    Expected: Route 2 (Squad_Finance/payroll_service, Cost 0.10).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'item': 'Standard License'},
        policy_constraints={'security_level': 3, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Squad_Finance/payroll_service'
    assert best_route.cost == 0.10


def test_02_policy_filtering_sensitive_data(gateway: AgentGatewayProtocol):
    """
    Verifies strict policy filtering excludes non-compliant routes regardless of cost.
    Constraint: requires_pii: True. Only Route 2 complies (Cost 0.10).
    Expected: Route 2 (Squad_Finance/payroll_service, Cost 0.10).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'item': 'Client Data License'},
        policy_constraints={'requires_pii': True},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Squad_Finance/payroll_service'
    assert best_route.cost == 0.10


def test_03_route_not_found(gateway: AgentGatewayProtocol):
    """Tests routing failure when the target capability is not in the AGPTable."""
    intent = IntentPayload(
        target_capability='unknown:capability', payload={'data': 'test'}
    )
    best_route = gateway.route_intent(intent)
    assert best_route is None


def test_04_policy_violation_unmatched_constraint(
    gateway: AgentGatewayProtocol,
):
    """
    Tests routing failure when the Intent imposes a constraint that no announced route can meet.
    Constraint: security_level: 7. No route announces level 7 or higher.
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'item': 'Executive Access'},
        policy_constraints={'security_level': 7},
    )
    best_route = gateway.route_intent(intent)
    assert best_route is None


def test_05_announcement_updates_table(gateway: AgentGatewayProtocol):
    """Tests that announce_capability correctly adds a new entry to the AGPTable."""
    announcement = CapabilityAnnouncement(
        capability='test:add:new',
        version='1.0',
        cost=1.0,
        policy={'test': True, 'security_level': 1},
    )
    path = 'TestSquad/target'

    # Check table before announcement
    assert 'test:add:new' not in gateway.agp_table.routes

    gateway.announce_capability(announcement, path)

    # Check table after announcement
    assert 'test:add:new' in gateway.agp_table.routes
    assert len(gateway.agp_table.routes['test:add:new']) == 1
    assert gateway.agp_table.routes['test:add:new'][0].path == path


# --- NEW TEST CASE FOR META-INTENT DECOMPOSITION ---


def test_06_meta_intent_decomposition(gateway: AgentGatewayProtocol):
    """
    Simulates the Corporate Enterprise flow: decomposition into three sub-intents
    and verifies each sub-intent routes to the correct specialist squad based on policies.
    """

    # 1. Hardware Sub-Intent (Standard Engineering Task, requires level 3)
    intent_hardware = IntentPayload(
        target_capability='provision:hardware',
        payload={'developer': 'Alice'},
        policy_constraints={'security_level': 3},
    )
    route_hw = gateway.route_intent(intent_hardware)
    assert route_hw is not None
    assert route_hw.path == 'Squad_Engineering/hardware_tool'

    # 2. Payroll Sub-Intent (Requires PII Handling - must go to secure Finance squad)
    intent_payroll = IntentPayload(
        target_capability='provision:payroll',
        payload={'salary': 100000},
        policy_constraints={'requires_pii': True, 'security_level': 3},
    )
    route_payroll = gateway.route_intent(intent_payroll)
    assert route_payroll is not None
    assert route_payroll.path == 'Squad_Finance/payroll_service'

    # 3. Legal Sub-Intent (Simple route for contract:nda:generate, requires level 3)
    intent_legal = IntentPayload(
        target_capability='contract:nda:generate',
        payload={'contract_type': 'NDA'},
        policy_constraints={'security_level': 3},
    )
    route_legal = gateway.route_intent(intent_legal)
    assert route_legal is not None
    assert route_legal.path == 'Squad_Legal/contracts_tool'
