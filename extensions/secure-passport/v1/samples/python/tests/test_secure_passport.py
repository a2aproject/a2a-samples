import pytest
from secure_passport_ext import (
    CallerContext, 
    A2AMessage,         
    add_secure_passport, 
    get_secure_passport, 
    SECURE_PASSPORT_URI,
)

# ======================================================================
## Fixtures for Core Tests
# ======================================================================

@pytest.fixture
def valid_passport_data():
    """
    Returns a dictionary for creating a valid CallerContext. 
    Keys are snake_case to align with the final CallerContext model attributes.
    """
    return {
        "client_id": "a2a://orchestrator.com", # CORRECTED: Changed agent_id to client_id
        "session_id": "session-123",
        "state": {"currency": "USD", "tier": "silver"},
        "signature": "mock-signature-xyz"
    }

# ======================================================================
## Core Functionality Tests
# ======================================================================

def test_add_and_get_passport_success(valid_passport_data):
    """Tests successful serialization and deserialization in a round trip."""
    passport = CallerContext(**valid_passport_data)
    message = A2AMessage() 
    
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    assert retrieved is not None
    assert retrieved.client_id == "a2a://orchestrator.com" # CORRECTED: Access via client_id
    assert retrieved.state == {"currency": "USD", "tier": "silver"}

def test_get_passport_when_missing():
    """Tests retrieving a passport from a message that doesn't have one."""
    message = A2AMessage() 
    retrieved = get_secure_passport(message)
    assert retrieved is None

def test_passport_validation_failure_missing_required_field(valid_passport_data):
    """Tests validation fails when a required field (client_id) is missing."""
    invalid_data = valid_passport_data.copy()
    del invalid_data['client_id'] # CORRECTED: Deleting client_id key
    
    message = A2AMessage() 
    message.metadata[SECURE_PASSPORT_URI] = invalid_data
    
    retrieved = get_secure_passport(message)
    assert retrieved is None

def test_passport_validation_failure_extra_field(valid_passport_data):
    """Tests validation fails when an unknown field is present (due to extra='forbid')."""
    invalid_data = valid_passport_data.copy()
    invalid_data['extra_field'] = 'unsupported'
    
    message = A2AMessage() 
    message.metadata[SECURE_PASSPORT_URI] = invalid_data
    
    retrieved = get_secure_passport(message)
    assert retrieved is None

def test_passport_is_verified_with_signature(valid_passport_data):
    """Tests that the is_verified property is True when a signature is present."""
    passport = CallerContext(**valid_passport_data)
    assert passport.is_verified is True

def test_passport_is_unverified_without_signature(valid_passport_data):
    """Tests that the is_verified property is False when the signature is missing."""
    data_without_sig = valid_passport_data.copy()
    data_without_sig['signature'] = None 
    passport = CallerContext(**data_without_sig)
    assert passport.is_verified is False

def test_retrieved_passport_is_immutable_from_message_data(valid_passport_data):
    """Tests that modifying the retrieved copy's state does not change the original message metadata (due to deepcopy)."""
    passport = CallerContext(**valid_passport_data)
    message = A2AMessage() 
    add_secure_passport(message, passport)

    retrieved = get_secure_passport(message)
    retrieved.state['new_key'] = 'changed_value'
    
    original_data = message.metadata[SECURE_PASSPORT_URI]['state']
    
    assert 'new_key' not in original_data
    assert original_data['currency'] == 'USD'


# ======================================================================
## Use Case Integration Tests
# ======================================================================

def test_use_case_1_currency_conversion():
    """Verifies the structure for passing a user's currency preference."""
    state_data = {
        "user_preferred_currency": "GBP",
        "user_id": "U001"
    }
    
    passport = CallerContext(
        client_id="a2a://travel-orchestrator.com", # CORRECTED: Using client_id keyword
        state=state_data,
        signature="sig-currency-1"
    )
    
    message = A2AMessage() 
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    assert retrieved.state.get("user_preferred_currency") == "GBP"
    assert retrieved.is_verified is True

def test_use_case_2_personalized_travel_booking():
    """Verifies the structure for passing detailed session and loyalty data."""
    state_data = {
        "destination": "Bali, Indonesia",
        "dates": "2025-12-01 to 2025-12-15",
        "loyalty_tier": "Platinum"
    }
    
    passport = CallerContext(
        client_id="a2a://travel-portal.com", # CORRECTED: Using client_id keyword
        session_id="travel-booking-session-999", 
        state=state_data,
        signature="sig-travel-2"
    )
    
    message = A2AMessage() 
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    assert retrieved.session_id == "travel-booking-session-999"
    assert retrieved.state.get("loyalty_tier") == "Platinum"
    assert retrieved.is_verified is True

def test_use_case_3_proactive_retail_assistance():
    """Verifies the structure for passing product context for assistance."""
    state_data = {
        "product_sku": "Nikon-Z-50mm-f1.8",
        "cart_status": "in_cart",
        "user_intent": "seeking_reviews"
    }
    
    passport = CallerContext(
        client_id="a2a://ecommerce-front.com", # CORRECTED: Using client_id keyword
        state=state_data,
    )
    
    message = A2AMessage() 
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    assert retrieved.state.get("product_sku") == "Nikon-Z-50mm-f1.8"
    assert retrieved.is_verified is False
    assert retrieved.session_id is None

def test_use_case_4_secured_db_insights():
    """Verifies the structure for passing required request arguments for a secured DB/ERP agent."""
    state_data = {
        "query_type": "quarterly_revenue",
        "time_period": {"start": "2025-07-01", "end": "2025-09-30"},
        "access_scope": ["read:finance_db", "user:Gulli"]
    }
    
    passport = CallerContext(
        client_id="a2a://marketing-agent.com", # CORRECTED: Using client_id keyword
        state=state_data,
        signature="sig-finance-4" 
    )
    
    message = A2AMessage() 
    add_secure_passport(message, passport)
    retrieved = get_secure_passport(message)
    
    assert retrieved.state.get("query_type") == "quarterly_revenue"
    assert "read:finance_db" in retrieved.state.get("access_scope")
    assert retrieved.is_verified is True
