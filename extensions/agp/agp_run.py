from agp_protocol.__init__ import (
    AgentGatewayProtocol,
    AGPTable,
    IntentPayload,
    CapabilityAnnouncement,
    RouteEntry
)

# --- PHASE 1: Setup and Announcement ---

# 1. Initialize the central routing table
CORPORATE_AGP_TABLE = AGPTable()

# 2. Initialize the Corporate Gateway Agent (Router)
corporate_gateway = AgentGatewayProtocol(
    squad_name="Corporate_GW",
    agp_table=CORPORATE_AGP_TABLE
)

# 3. Squads announce their capabilities to the Corporate Gateway

print("===============================================================")
print("      AGENT GATEWAY PROTOCOL (AGP) ROUTING SIMULATION")
print("===============================================================")
print("\n--- PHASE 1: SQUAD ANNOUNCEMENTS ---")

# --- Announcement 1: Engineering Squad (Internal, Secure) ---
# Can provision VMs, handles sensitive data (PII), but is more expensive than the external vendor.
eng_announcement = CapabilityAnnouncement(
    capability="infra:provision:vm",
    version="1.0",
    cost=0.10, # Higher cost
    policy={
        "security_level": 5,
        "requires_PII": True 
    }
)
corporate_gateway.announce_capability(
    eng_announcement,
    path="Squad_Engineering/vm_provisioner"
)

# --- Announcement 2: External Vendor Squad (Cheapest, Low Security) ---
# Can provision VMs, but fails the PII check and only meets standard security.
vendor_announcement = CapabilityAnnouncement(
    capability="infra:provision:vm",
    version="1.1",
    cost=0.05, # Lowest cost
    policy={
        "security_level": 3,
        "requires_PII": False 
    }
)
corporate_gateway.announce_capability(
    vendor_announcement,
    path="External_Vendor/vm_provisioning_api"
)

# --- Announcement 3: Finance Squad (Standard Analysis) ---
finance_announcement = CapabilityAnnouncement(
    capability="financial_analysis:quarterly",
    version="2.0",
    cost=0.15,
    policy={
        "security_level": 3,
        "geo": "US"
    }
)
corporate_gateway.announce_capability(
    finance_announcement,
    path="Squad_Finance/analysis_tool"
)


# --- PHASE 2: Intent Routing Simulation ---

print("\n--- PHASE 2: INTENT ROUTING ---")

# Intent A: Standard VM provisioning (Cost-driven, minimal policy)
intent_a = IntentPayload(
    target_capability="infra:provision:vm",
    payload={"type": "standard", "user": "bob"},
    metadata={"security_level": 3}
)
print(f"\n[Intent A] Requesting standard VM provisioning (Lowest cost, Security Level 3).")
corporate_gateway.route_intent(intent_a)


# Intent B: Sensitive VM provisioning (Policy-driven, requires PII)
# This intent fails the External Vendor (Cost 0.05) and must be routed to Engineering (Cost 0.10).
intent_b = IntentPayload(
    target_capability="infra:provision:vm",
    payload={"type": "sensitive", "user": "alice", "data": "ssn_data"},
    metadata={"security_level": 5, "requires_PII": True}
)
print(f"\n[Intent B] Requesting sensitive VM provisioning (Requires PII and Security Level 5).")
corporate_gateway.route_intent(intent_b)


# Intent C: Requesting provisioning with security level 7 (Unmatched Policy)
# No announced route can satisfy level 7.
intent_c = IntentPayload(
    target_capability="infra:provision:vm",
    payload={"type": "max_security"},
    metadata={"security_level": 7}
)
print(f"\n[Intent C] Requesting provisioning with security level 7 (Unmatched Policy).")
corporate_gateway.route_intent(intent_c)


# Intent D: Requesting HR onboarding (Unknown Capability)
# This intent fails because the capability was never announced.
intent_d = IntentPayload(
    target_capability="hr:onboard:new_hire",
    payload={"employee": "Charlie"},
    metadata={}
)
print(f"\n[Intent D] Requesting HR onboarding (Unknown Capability).")
corporate_gateway.route_intent(intent_d)

