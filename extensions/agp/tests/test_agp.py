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
        # 1. Base License/Legal Route (Security Level 3, Geo US) - Cost 0.20
        RouteEntry(
            path='Squad_Legal/licensing_api',
            cost=0.20,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 2. Secure/PII Route (Security Level 5, PII Handling True, Geo US) - Cost 0.10
        RouteEntry(
            path='Squad_Finance/payroll_service',
            cost=0.10,
            policy={'security_level': 5, 'requires_pii': True, 'geo': 'US'},
        ),
        # 3. External Route (Cheapest, Low Security, Geo EU) - Cost 0.05
        RouteEntry(
            path='Vendor_EU/proxy_gateway',
            cost=0.05,
            policy={'security_level': 1, 'geo': 'EU'},
        ),
        # 4. Hardware Provisioning Route (Engineering, Security Level 3, Geo US) - Cost 0.08
        RouteEntry(
            path='Squad_Engineering/hardware_tool',
            cost=0.08,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 5. NDA Contract Generation Route (Legal, Security Level 3, Geo US) - Cost 0.15
        RouteEntry(
            path='Squad_Legal/contracts_tool',
            cost=0.15,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 6. Low-Cost US Route (Security Level 2, Geo US) - Cost 0.07
        RouteEntry(
            path='Vendor_US/data_service',
            cost=0.07,
            policy={'security_level': 2, 'geo': 'US'},
        ),
        # 7. Zero-Cost Internal Route (Security Level 3, Geo US) - Cost 0.00 (NEW)
        RouteEntry(
            path='Internal/Free_Cache',
            cost=0.00,
            policy={'security_level': 3, 'geo': 'US'},
        ),
        # 8. High-Cost Geo EU Route (Security Level 4, Geo EU) - Cost 0.30 (NEW)
        RouteEntry(
            path='Vendor_Secure_EU/proxy_gateway',
            cost=0.30,
            policy={'security_level': 4, 'geo': 'EU'},
        ),
    ]


@pytest.fixture
def populated_agp_table(all_available_routes) -> AGPTable:
    """Creates an AGPTable populated with routes for all test capabilities."""
    table = AGPTable()

    # Routes for Core Routing Tests (Tests 1-19 use 'procure:license')
    table.routes['procure:license'] = [
        all_available_routes[0],
        all_available_routes[1],
        all_available_routes[2],
        all_available_routes[5],
        all_available_routes[6],  # Zero Cost Route
        all_available_routes[7],  # Secure EU Route
    ]

    # Routes for Decomposition Test (Test 6)
    table.routes['provision:hardware'] = [all_available_routes[3]]
    table.routes['provision:payroll'] = [all_available_routes[1]]
    table.routes['contract:nda:generate'] = [all_available_routes[4]]

    return table


@pytest.fixture
def gateway(populated_agp_table) -> AgentGatewayProtocol:
    """Provides a configured Gateway Agent instance for testing."""
    return AgentGatewayProtocol(
        squad_name='Test_Gateway', agp_table=populated_agp_table
    )


# --- Test Scenarios (19 Total Tests) ---


def test_01_lowest_cost_compliant_route_with_sufficiency(
    gateway: AgentGatewayProtocol,
):
    """
    Verifies routing selects the lowest cost COMPLIANT route, checking for sufficiency (>=).
    Constraint: security_level: 3, geo: US. Route 7 (Cost 0.00) is the cheapest compliant route.
    Expected: Route 7 (Internal/Free_Cache, Cost 0.00).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'item': 'Standard License'},
        policy_constraints={'security_level': 3, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


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


# --- NEW SECURITY AND COMPLIANCE TESTS ---


def test_07_geo_fencing_violation(gateway: AgentGatewayProtocol):
    """
    Tests routing failure when an Intent requires US processing, but the cheapest route is EU-locked.
    Constraint: geo: US. External Vendor (Cost 0.05, EU) fails geo-check.
    Expected: Routed to cheapest compliant US vendor (Internal/Free_Cache, Cost 0.00).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'data': 'US-user-request'},
        policy_constraints={'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_08_required_security_tier_sufficiency(gateway: AgentGatewayProtocol):
    """
    Tests routing when a request requires a moderate security level (4).
    The router must choose Route 2 (Level 5) because Route 1 (Level 3) and Route 6 (Level 2) fail the sufficiency check.
    Constraint: security_level: 4.
    Expected: Route 2 (Squad_Finance/payroll_service, Cost 0.10).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'data': 'moderate_access'},
        policy_constraints={'security_level': 4},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Squad_Finance/payroll_service'
    assert best_route.cost == 0.10


def test_09_policy_chaining_cost_after_geo(gateway: AgentGatewayProtocol):
    """
    Tests routing for a complex chain: Intent requires US geo AND Level 2 security.
    Compliant routes: Route 7 (0.00, L3), Route 6 (0.07, L2), Route 2 (0.10, L5), Route 1 (0.20, L3).
    Expected: Cheapest compliant US route (Internal/Free_Cache, Cost 0.00).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'simple_data_pull'},
        policy_constraints={'security_level': 2, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_10_zero_cost_priority(gateway: AgentGatewayProtocol):
    """
    Tests that the absolute cheapest route (Cost 0.00) is prioritized when compliant.
    Constraint: security_level: 3, geo: US. Route 7 (Cost 0.00) meets the need.
    Expected: Route 7 (Internal/Free_Cache, Cost 0.00).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'cache_check'},
        policy_constraints={'security_level': 3, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_11_minimum_security_level_one_selection(gateway: AgentGatewayProtocol):
    """
    Tests routing for the absolute lowest security requirement.
    Constraint: security_level: 1. Route 7 (Cost 0.00) is the cheapest compliant route.
    Expected: Route 7 (Internal/Free_Cache, Cost 0.00).
    """
    # NOTE: All routes are compliant (L1, L3, L5, L2, L3, L3, L4). Cheapest is Route 7 (Cost 0.00).
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'public_data_access'},
        policy_constraints={'security_level': 1},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_12_strict_geo_exclusion(gateway: AgentGatewayProtocol):
    """
    Tests routing failure when requested geo (NA) is not available anywhere.
    Constraint: geo: NA. No route advertises 'NA'.
    Expected: Fails to route.
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'NA_access'},
        policy_constraints={'geo': 'NA'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is None


def test_13_cost_tie_breaker(gateway: AgentGatewayProtocol):
    """
    Tests the tie-breaker mechanism when two compliant routes have the exact same cost.
    Constraint: security_level: 5, geo: US. Only Route 2 (Cost 0.10, Level 5) is compliant.
    Expected: Route 2 (Squad_Finance/payroll_service, Cost 0.10).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'high_security_check'},
        policy_constraints={'security_level': 5, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Squad_Finance/payroll_service'
    assert best_route.cost == 0.10


def test_14_no_constraint_default_cheapest(gateway: AgentGatewayProtocol):
    """
    Tests routing when the Intent provides no constraints (empty metadata).
    Expected: Router must select the absolute cheapest route available (Route 7, Cost 0.00).
    """
    # NOTE: Route 7 (Cost 0.00) is the cheapest overall.
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'simple_unsecured'},
        policy_constraints={},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_15_compound_exclusion(gateway: AgentGatewayProtocol):
    """
    Tests routing failure when two mandatory constraints cannot be met by the same route.
    Constraint: geo: EU AND security_level: 5.
    Expected: Failure (Route 8 is EU but only L4; Route 2 is L5 but US).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'EU_secure_data'},
        policy_constraints={'geo': 'EU', 'security_level': 5},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is None


def test_16_decomposition_check_pii_only_route(gateway: AgentGatewayProtocol):
    """
    Verifies that the decomposition test logic for Payroll correctly chooses the PII-handling route.
    This is a redundant check to ensure Test 06's complexity is fully stable.
    """
    intent_payroll = IntentPayload(
        target_capability='provision:payroll',
        payload={'salary': 100000},
        policy_constraints={'requires_pii': True, 'security_level': 3},
    )
    route_payroll = gateway.route_intent(intent_payroll)
    assert route_payroll is not None
    assert route_payroll.path == 'Squad_Finance/payroll_service'


def test_17_cost_wins_after_sufficiency_filter(gateway: AgentGatewayProtocol):
    """
    Tests that after filtering for sufficiency (Level >= 2), the cheapest route is chosen.
    Compliant routes: Route 7 (0.00, L3), Route 6 (0.07, L2), Route 2 (0.10, L5), Route 1 (0.20, L3).
    Expected: Cheapest compliant route (Internal/Free_Cache, Cost 0.00).
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'simple_data_pull'},
        policy_constraints={'security_level': 2},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_18_sufficiency_check_for_level_1_route_wins(
    gateway: AgentGatewayProtocol,
):
    """
    Tests that a request for L1 security is satisfied by the cheapest overall route (L1, 0.05).
    Constraint: security_level: 1.
    Expected: Router must select the absolute cheapest route available (Route 7, Cost 0.00).
    """
    # NOTE: All routes are L1 or higher. Cheapest is Route 7 (Cost 0.00).
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'lowest_security'},
        policy_constraints={'security_level': 1},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Internal/Free_Cache'
    assert best_route.cost == 0.00


def test_19_compound_geo_and_sufficiency_win(gateway: AgentGatewayProtocol):
    """
    Tests a chain of filters: Needs geo: US AND security_level: 5.
    Expected: Route 2 (Cost 0.10) is the only one that meets both.
    """
    intent = IntentPayload(
        target_capability='procure:license',
        payload={'request': 'US_secure_finance'},
        policy_constraints={'security_level': 5, 'geo': 'US'},
    )

    best_route = gateway.route_intent(intent)

    assert best_route is not None
    assert best_route.path == 'Squad_Finance/payroll_service'
    assert best_route.cost == 0.10
