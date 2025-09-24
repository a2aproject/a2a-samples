from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from copy import deepcopy

# --- Extension Definition ---

SECURE_PASSPORT_URI = "https://a2aprotocol.ai/ext/secure-passport/v1"

class CallerContext(BaseModel):
    """
    The Secure Passport payload containing contextual state shared by the calling agent.
    """
    agentId: str = Field(..., description="The verifiable unique identifier of the calling agent.")
    signature: Optional[str] = Field(None, description="A cryptographic signature of the 'state' payload.")
    sessionId: Optional[str] = Field(None, description="A session or conversation identifier for continuity.")
    state: Dict[str, Any] = Field(..., description="A free-form JSON object containing the contextual data.")
    
    # Use ConfigDict for Pydantic V2 compatibility
    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True
    )
    
    @property
    def is_verified(self) -> bool:
        """
        Conceptually checks if the passport contains a valid signature.
        Returns True if a signature string is present, and False otherwise.
        """
        return self.signature is not None

# --- Helper Functions (Core Protocol Interaction) ---

# Mock class representing a core A2A message for demonstration
class MockA2AMessage(BaseModel):
    """A minimal representation of a core A2A Message structure."""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
def add_secure_passport(message: MockA2AMessage, context: CallerContext) -> None:
    """Adds the Secure Passport (CallerContext) to the message's metadata."""
    message.metadata[SECURE_PASSPORT_URI] = context.model_dump(exclude_none=True)

def get_secure_passport(message: MockA2AMessage) -> Optional[CallerContext]:
    """Retrieves and validates the Secure Passport from the message metadata."""
    passport_data = message.metadata.get(SECURE_PASSPORT_URI)
    if not passport_data:
        return None

    try:
        # Use deepcopy to ensure the consuming agent does not mutate the original message data
        return CallerContext.model_validate(deepcopy(passport_data))
    except ValidationError as e:
        # In a real SDK, this would be logged more formally
        print(f"ERROR: Received malformed Secure Passport data. Ignoring payload: {e}")
        return None

# ======================================================================
# Convenience and Middleware Concepts
# ======================================================================

class SecurePassportExtension:
    """
    A conceptual class containing static methods for extension utilities 
    and defining middleware layers for seamless integration.
    """
    @staticmethod
    def get_agent_card_declaration(supported_state_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generates the JSON structure required to declare support for this 
        extension in an A2A AgentCard.
        """
        declaration = {
            "uri": SECURE_PASSPORT_URI,
            "params": {
                "receivesCallerContext": True
            }
        }
        if supported_state_keys:
            declaration["params"]["supportedStateKeys"] = supported_state_keys
        
        return declaration

    @staticmethod
    def client_middleware(next_handler, message: MockA2AMessage, context: CallerContext):
        """
        [Conceptual Middleware Layer: Client/Calling Agent]
        
        Executes before sending the message. Automatically attaches the passport.
        """
        # In a real SDK, this print would be a log statement
        print(f"[Middleware: Client] Attaching Secure Passport for {context.agentId}")
        add_secure_passport(message, context)
        return next_handler(message) # Passes the augmented message to the transport layer

    @staticmethod
    def server_middleware(next_handler, message: MockA2AMessage):
        """
        [Conceptual Middleware Layer: Server/Receiving Agent]
        
        Executes after receiving the message. Extracts the passport, validates, 
        and passes the context to the agent's core handler.
        """
        passport = get_secure_passport(message)
        
        if passport:
            print(f"[Middleware: Server] Extracted Secure Passport. Verified: {passport.is_verified}")
        else:
            print("[Middleware: Server] No Secure Passport found or validation failed.")
            
        # next_handler is the agent's core task logic. We pass the message and the extracted passport.
        return next_handler(message, passport)
