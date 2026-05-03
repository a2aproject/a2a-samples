"""Central configuration for the SAP Maintenance Order Agent."""

import os

# ---------------------------------------------------------------------------
# LLM Configuration
# ---------------------------------------------------------------------------
DEFAULT_LLM_MODEL = "gpt-4o"
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", DEFAULT_LLM_MODEL)

# ---------------------------------------------------------------------------
# PEOS Graph Configuration
# ---------------------------------------------------------------------------
MAX_EXECUTOR_ITERATIONS = int(os.getenv("MAX_EXECUTOR_ITERATIONS", "10"))
MAX_HISTORY_MESSAGES = 40
MAX_QUERY_LENGTH = 2000
E2E_TIMEOUT_SECONDS = 55.0

# ---------------------------------------------------------------------------
# SAP Connection (set USE_MOCK_DATA=false + credentials to connect to real S/4HANA)
# ---------------------------------------------------------------------------
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
SAP_BASE_URL = os.getenv("SAP_BASE_URL", "")
SAP_USER = os.getenv("SAP_USER", "")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "")
SAP_CLIENT = os.getenv("SAP_CLIENT", "100")

# ---------------------------------------------------------------------------
# Tool Policy
# ---------------------------------------------------------------------------
TOOL_POLICY_MODE = os.getenv("TOOL_POLICY_MODE", "permissive").strip().lower()
ENABLE_WRITE_ACTIONS = os.getenv("ENABLE_WRITE_ACTIONS", "false").strip().lower() == "true"

# ---------------------------------------------------------------------------
# Quick Replies (≤28 chars each — UI rendering limit)
# ---------------------------------------------------------------------------
QUICK_REPLY_MAX_LEN = 28
DEFAULT_QUICK_REPLIES = [
    "Orders needing attention",   # 24 chars
    "Get first order details",    # 23 chars
    "Check confirmations",        # 19 chars
]

# ---------------------------------------------------------------------------
# Phase/SubPhase Maps — SAP API_MAINTENANCEORDER v0002 (9-phase model)
# Public API: https://api.sap.com/api/API_MAINTENANCEORDER/overview
# ---------------------------------------------------------------------------
PHASE_MAP = {
    "01": "Initiation",
    "02": "Screening",
    "03": "Planning",
    "04": "Approval",
    "05": "Preparation",
    "06": "Scheduling",
    "07": "Execution",
    "08": "Post Execution",
    "09": "Completion",
}

ORDER_SUBPHASE_MAP = {
    "0035": "In Planning",
    "0040": "Submitted for Approval",
    "0045": "Approved",
    "0050": "Rejected",
    "0055": "In Preparation",
    "0060": "Ready to Schedule",
    "0065": "Ready for Execution",
    "0070": "Main Work Started",
    "0075": "Main Work Completed",
    "0080": "Work Done",
    "0085": "Technically Complete",
    "0092": "Work Not Performed",
    "0095": "Closed",
    "0105": "Deletion Flag",
}

OPERATION_SUBPHASE_MAP = {
    "0110": "In Planning",
    "0115": "In Preparation",
    "0120": "Ready to Schedule",
    "0125": "Ready for Execution",
    "0130": "Work in Execution",
    "0135": "Work Paused",
    "0140": "Work Finished",
    "0145": "Technically Complete",
    "0150": "Closed",
}

# ---------------------------------------------------------------------------
# Agent Capabilities (zero LLM cost — returned directly for "what can you do?")
# ---------------------------------------------------------------------------
AGENT_CAPABILITIES = """
**I'm the SAP Maintenance Order Analyst.** Here's what I can help with:

**🔍 Search & Discovery**
- Find maintenance orders by plant, priority, work center, date range, material, status
- Filter by 9-phase model: phase (Initiation→Completion) and sub-phase
- Search equipment by plant, functional location, manufacturer
- Show orders ready for supervisor review (TECO candidates)

**📋 Order Details**
- Complete order context (header, operations, components, costs)
- Phase & sub-phase status, linked notifications with damage/cause codes
- Confirmation status (time, failure codes, measurements)

**📦 Inventory & Materials**
- Stock levels by plant/storage location
- Material shortages across orders
- Goods movement history

**🔧 Equipment & Locations**
- Equipment master data lookup
- Functional location hierarchy

**✅ Actions (with confirmation)**
- Set orders to Technically Complete (TECO)
- Reset TECO status

**Example questions:**
- "Show high priority orders for plant 1010"
- "Get details for order 4000045"
- "Check stock for material 100-100"
"""

# ---------------------------------------------------------------------------
# Search Field Catalog — documents OData filters available for search tool
# Uses public field names from SAP API Business Hub
# ---------------------------------------------------------------------------
SEARCH_FIELD_CATALOG = {
    "plant": {
        "tool_param": "plant",
        "odata_field": "MaintenancePlanningPlant",
        "example": "1010",
    },
    "priority": {
        "tool_param": "priority",
        "odata_field": "MaintPriority",
        "example": "1 (Critical), 2 (High), 3 (Medium), 4 (Low)",
    },
    "work_center": {
        "tool_param": "work_center",
        "odata_field": "MainWorkCenter",
        "example": "MECH_WC",
    },
    "order_type": {
        "tool_param": "order_type",
        "odata_field": "MaintenanceOrderType",
        "example": "PM01",
    },
    "equipment": {
        "tool_param": "equipment",
        "odata_field": "TechnicalObject",
        "example": "10000123",
    },
    "functional_location": {
        "tool_param": "functional_location",
        "odata_field": "FunctionalLocation",
        "example": "FN-1000",
    },
    "phase": {
        "tool_param": "phase",
        "odata_field": "MaintOrdProcessPhaseCode",
        "example": "03 or PLANNING",
    },
    "subphase": {
        "tool_param": "subphase",
        "odata_field": "MaintOrdProcessSubPhaseCode",
        "example": "0065 or READY_FOR_EXECUTION",
    },
}
