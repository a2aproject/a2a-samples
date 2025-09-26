from typing import Optional, Dict, Any, List, Callable
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from copy import deepcopy
import logging

# --- Import official A2A types ---
# Assuming the official A2A message type is available here:
try:
    from a2a.types import A2AMessage
except ImportError:
    # Fallback/Placeholder if official package is not fully installed locally
    class A2AMessage(BaseModel):
        metadata: Dict[str, Any] = Field(default_factory=dict)
        
# --- Extension Definition ---

SECURE_PASSPORT_URI = "https://a2a-protocol.org/ext/secure-passport/v1"

class CallerContext(BaseModel):
    """
    The Secure Passport payload containing contextual state shared by the calling agent.
    """
    # PEP 8 Compliant (snake_case) with JSON mapping (camelCase alias)
    agent_id: str = Field(..., alias='agentId', description="The verifiable unique identifier of the calling agent.")
    signature: Optional[str] = Field(None, alias='signature', description="A cryptographic signature of the 'state' payload.")
    session_id: Optional[str] = Field(None, alias='sessionId', description="A session or conversation identifier for continuity.")
    state: Dict[str, Any] = Field(..., description="A free-form JSON object containing the contextual data.")
    
    # Use ConfigDict for Pydantic V2 compatibility and configuration
    model_config = ConfigDict(
        # Allows instantiation using either the JSON alias or the Python field name
        populate_by_name=True, 
        extra='forbid'
    )
    
    @property
    def is_verified(self) -> bool:
        """
        Conceptually checks if the passport contains a valid signature.
        """
        return self.signature is not None

# --- Helper Functions (Core Protocol Interaction) ---
    
def add_secure_passport(message: A2AMessage, context: CallerContext) -> None:
    """Adds the Secure Passport (CallerContext) to the message's metadata."""
    
    # by_alias=True ensures the output JSON uses the correct camelCase names
    message.metadata[SECURE_PASSPORT_URI] = context.model_dump(by_alias=True, exclude_none=True)

def get_secure_passport(message: A2AMessage) -> Optional[CallerContext]:
    """Retrieves and validates the Secure Passport from the message metadata."""
    passport_data = message.metadata.get(SECURE_PASSPORT_URI)
    if not passport_data:
        return None

    try:
        # validate uses aliases implicitly for input conversion
        return CallerContext.model_validate(deepcopy(passport_data))
    except ValidationError as e:
        # logging is already used here
        logging.warning(f"ERROR: Received malformed Secure Passport data. Ignoring payload: {e}")
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
            "params": {}
        }
        
        if supported_state_keys:
            declaration["params"]["supportedStateKeys"] = supported_state_keys
            
        return declaration

    @staticmethod
    def client_middleware(next_handler: Callable[[A2AMessage], Any], message: A2AMessage, context: CallerContext):
        """
        [Conceptual Middleware Layer: Client/Calling Agent]
        
        Type Hint: next_handler takes one A2AMessage and returns Any.
        """
        logging.info(f"[Middleware: Client] Attaching Secure Passport for {context.agent_id}")
        add_secure_passport(message, context)
        return next_handler(message) # Passes the augmented message to the transport layer

    @staticmethod
    def server_middleware(next_handler: Callable[[A2AMessage, Optional[CallerContext]], Any], message: A2AMessage):
        """
        [Conceptual Middleware Layer: Server/Receiving Agent]
        
        Type Hint: next_handler takes A2AMessage and Optional[CallerContext] and returns Any.
        """
        passport = get_secure_passport(message)
        
        if passport:
            logging.info(f"[Middleware: Server] Extracted Secure Passport. Verified: {passport.is_verified}")
        else:
            logging.debug("[Middleware: Server] No Secure Passport found or validation failed.")
            
        # next_handler is the agent's core task logic. We pass the message and the extracted passport.
        return next_handler(message, passport)
