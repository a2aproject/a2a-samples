# Secure Passport Python Sample

This sample provides the runnable code for the **Secure Passport Extension v1** for the Agent2Agent (A2A) protocol, demonstrating its implementation and usage in a Python environment.

## 1. Extension Overview

The core of this extension is the **`CallerContext`** data model, which is attached to the A2A message metadata under the extension's unique URI. This enables the secure transfer of trusted contextual state between collaborating agents.

### Extension URI

The unique identifier for this extension is:
`https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport`

---

## 2. Comprehensive Usage and Middleware Demonstration

The `run.py` script demonstrates the full client-server pipeline using the conceptual **middleware layers** for seamless integration.

### A. Use Case Code Demonstration

The following code demonstrates how to create the specific `CallerContext` payloads for the four core use cases, verifying that the structure and integrity checks work as intended.

```python
from secure_passport_ext import (
    CallerContext, 
    A2AMessage, 
    add_secure_passport, 
    get_secure_passport
)

def demonstrate_use_case(title: str, client_id: str, state: dict, signature: str | None = None, session_id: str | None = None):
    print(f"\n--- Demonstrating: {title} ---")
    
    passport = CallerContext(
        client_id=client_id,
        session_id=session_id,
        signature=signature,
        state=state
    )

    message = A2AMessage()
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    if retrieved:
        print(f"  Source: {retrieved.client_id}")
        print(f"  Verified: {retrieved.is_verified}")
        print(f"  Context: {retrieved.state}")
    else:
        print("  [ERROR] Passport retrieval failed.")

# 1. Efficient Currency Conversion (Low Context, High Trust)

demonstrate_use_case(
    title="1. Currency Conversion (GBP)",
    client_id="a2a://travel-orchestrator.com",
    state={"user_preferred_currency": "GBP", "user_id": "U001"},
    signature="sig-currency-1"
)

# 2. Personalized Travel Booking (High Context, Session Data)

demonstrate_use_case(
    title="2. Personalized Travel (Platinum Tier)",
    client_id="a2a://travel-portal.com",
    session_id="travel-session-999",
    state={
        "destination": "Bali, Indonesia",
        "loyalty_tier": "Platinum"
    },
    signature="sig-travel-2"
)

# 3. Proactive Retail Assistance (Unsigned, Quick Context)

demonstrate_use_case(
    title="3. Retail Assistance (Unverified)",
    client_id="a2a://ecommerce-front.com",
    state={"product_sku": "Nikon-Z-50mm-f1.8", "user_intent": "seeking_reviews"},
    signature=None
)

# 4. Marketing Agent seek insights (High Trust, Secured Scope)

demonstrate_use_case(
    title="4. Secured DB Access (Finance)",
    client_id="a2a://marketing-agent.com",
    state={
        "query_type": "quarterly_revenue",
        "access_scope": ["read:finance_db", "user:Gulli"]
    },
    signature="sig-finance-4"
)
```

### B. Convenience Method: AgentCard Declaration

The `SecurePassportExtension` class provides a static method to easily generate the necessary JSON structure for including this extension in an agent's `AgentCard`. This ensures the structure is always compliant.

```python
from secure_passport_ext import SecurePassportExtension

# Scenario 1: Agent supports basic Secure Passport
simple_declaration = SecurePassportExtension.get_agent_card_declaration()
# Output will be: {'uri': '...', 'params': {'receivesCallerContext': True}}

# Scenario 2: Agent supports specific keys (e.g., the Travel Agent)
travel_keys = ["destination", "loyalty_tier", "dates"]
complex_declaration = SecurePassportExtension.get_agent_card_declaration(travel_keys)
# Output will include: 'supportedStateKeys': ['destination', 'loyalty_tier', 'dates']
```

## 3. How to Run the Sample 🚀

To run the sample and execute the comprehensive unit tests, follow these steps.

### A. Setup and Installation

1. **Navigate** to the Python sample directory:
    ```bash
    cd extensions/secure-passport/v1/samples/python
    ```
2. **Install Dependencies** (using Poetry):
    ```bash
    poetry install
    
    # Activate the virtual environment
    poetry shell
    ```

### B. Verification and Execution

#### 1. Run Unit Tests (Recommended)

Confirm all 11 core logic and validation tests pass:

```bash
pytest tests/
```

#### 2. Run Middleware Demo Script

Execute `run.py` to see the full client/server middleware pipeline in action for all four use cases:

```bash
python run.py
```
