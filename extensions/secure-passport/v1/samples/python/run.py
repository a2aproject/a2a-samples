# run.py

from secure_passport_ext import (
    CallerContext, 
    A2AMessage,             # CORRECTED: Importing the standardized A2AMessage type
    SecurePassportExtension # Import the extension utility class
)

# --- Define Mock Handlers for the Pipeline ---

def mock_transport_send(message: A2AMessage): # CORRECTED: Signature uses A2AMessage
    """Mocks the final step of the client sending the message over the wire."""
    print("  [Transport] Message sent over the wire.")
    return message # Returns the message the server would receive

def mock_agent_core_handler(message: A2AMessage, passport: CallerContext | None): # CORRECTED: Signature uses A2AMessage
    """
    Mocks the agent's core logic, which receives context from the Server Middleware.
    """
    print("  [Agent Core] Task received for processing.")
    
    if passport and passport.is_verified:
        # NOTE: Accessing the context attributes with snake_case
        currency = passport.state.get("user_preferred_currency", "Unknown")
        tier = passport.state.get("loyalty_tier", "Standard")
        print(f"  [Agent Core] Executing task with verified context: Currency={currency}, Tier={tier}")
    elif passport and not passport.is_verified:
        print("  [Agent Core] Executing task with unverified context (proceeding cautiously).")
    else:
        print("  [Agent Core] Executing task with no external context.")


def create_and_run_passport_test(client_id: str, session_id: str | None, state: dict, signature: str | None, use_case_title: str):
    """
    Demonstrates a full communication cycle using the conceptual middleware.
    """
    
    print(f"\n--- Use Case: {use_case_title} (via Middleware) ---")

    # 1. Orchestrator (Client) creates the Passport
    client_passport = CallerContext(
        client_id=client_id,
        session_id=session_id,
        signature=signature,
        state=state
    )

    # Mock A2A Message Container
    client_message = A2AMessage() 

    # --- CLIENT-SIDE PIPELINE ---
    print("  [PIPELINE] Client Side: Middleware -> Transport")
    
    message_over_wire = SecurePassportExtension.client_middleware(
        next_handler=mock_transport_send,
        message=client_message,
        context=client_passport
    )

    # --- SERVER-SIDE PIPELINE ---
    print("  [PIPELINE] Server Side: Middleware -> Agent Core")

    # Server Middleware is executed, wrapping the Agent Core Handler.
    SecurePassportExtension.server_middleware(
        next_handler=mock_agent_core_handler,
        message=message_over_wire
    )


def run_all_samples():
    print("=========================================================")
    print("      Secure Passport Extension Demo (Middleware)")
    print("=========================================================")

    # --- Use Case 1: Efficient Currency Conversion (High Trust Example) ---
    create_and_run_passport_test(
        client_id="a2a://travel-orchestrator.com",
        session_id=None,
        state={"user_preferred_currency": "GBP", "loyalty_tier": "Silver"},
        signature="sig-currency-1",
        use_case_title="Efficient Currency Conversion"
    )

    # --- Use Case 2: Personalized Travel Booking (High Context Example) ---
    create_and_run_passport_test(
        client_id="a2a://travel-portal.com",
        session_id="travel-booking-session-999",
        state={
            "destination": "Bali, Indonesia",
            "loyalty_tier": "Platinum"
        },
        signature="sig-travel-2",
        use_case_title="Personalized Travel Booking"
    )

    # --- Use Case 3: Proactive Retail Assistance (Unsigned/Low Trust Example) ---
    create_and_run_passport_test(
        client_id="a2a://ecommerce-front.com",
        session_id="cart-session-404",
        state={
            "product_sku": "Nikon-Z-50mm-f1.8",
            "user_intent": "seeking_reviews"
        },
        signature=None, # Explicitly missing signature
        use_case_title="Proactive Retail Assistance"
    )
    
    # --- Use Case 4: Marketing Agent seek insights (Secured Scope Example) ---
    create_and_run_passport_test(
        client_id="a2a://marketing-agent.com",
        session_id=None,
        state={
            "query_type": "quarterly_revenue",
            "access_scope": ["read:finance_db"]
        },
        signature="sig-finance-4",
        use_case_title="Marketing Agent seek insights"
    )


if __name__ == "__main__":
    run_all_samples()


    