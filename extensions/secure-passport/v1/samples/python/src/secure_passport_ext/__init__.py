# ruff: noqa: UP035, PLC0415, G004
from collections.abc import Callable
from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


# --- Extension Definition ---

SECURE_PASSPORT_URI = (
    'https://github.com/a2aproject/a2a-samples/tree/main/samples/python/extensions/secure-passport'
)


class CallerContext(BaseModel):
    """
    The Secure Passport payload containing contextual state shared by the calling agent.
    """

    # *** CORE CHANGE: agent_id renamed to client_id ***
    client_id: str = Field(
        ..., alias='clientId', description='The verifiable unique identifier of the calling client.'
    )
    signature: str | None = Field(
        None, alias='signature', description="A cryptographic signature of the 'state' payload."
    )
    session_id: str | None = Field(
        None, alias='sessionId', description='A session or conversation identifier for continuity.'
    )
    state: dict[str, Any] = Field(
        ..., description='A free-form JSON object containing the contextual data.'
    )

    # Use ConfigDict for Pydantic V2 compatibility and configuration
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    @property
    def is_verified(self) -> bool:
        """
        Conceptually checks if the passport contains a valid signature.
        """
        return self.signature is not None


# --- Helper Functions (Core Protocol Interaction) ---


class BaseA2AMessage(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


try:
    from a2a.types import A2AMessage
except ImportError:
    A2AMessage = BaseA2AMessage


def add_secure_passport(message: A2AMessage, context: CallerContext) -> None:
    """Adds the Secure Passport (CallerContext) to the message's metadata."""

    message.metadata[SECURE_PASSPORT_URI] = context.model_dump(by_alias=True, exclude_none=True)


def get_secure_passport(message: A2AMessage) -> CallerContext | None:
    """Retrieves and validates the Secure Passport from the message metadata."""
    passport_data = message.metadata.get(SECURE_PASSPORT_URI)
    if not passport_data:
        return None

    try:
        return CallerContext.model_validate(deepcopy(passport_data))
    except ValidationError as e:
        import logging

        logging.warning(f'ERROR: Received malformed Secure Passport data. Ignoring payload: {e}')
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
    def get_agent_card_declaration(supported_state_keys: list[str] | None = None) -> dict[str, Any]:
        """
        Generates the JSON structure required to declare support for this
        extension in an A2A AgentCard.
        """
        declaration = {'uri': SECURE_PASSPORT_URI, 'params': {}}
        if supported_state_keys:
            declaration['params']['supportedStateKeys'] = supported_state_keys

        return declaration

    @staticmethod
    def client_middleware(
        next_handler: Callable[[A2AMessage], Any], message: A2AMessage, context: CallerContext
    ):
        """
        [Conceptual Middleware Layer: Client/Calling Agent]
        """
        # ACCESS UPDATED: Use context.client_id
        print(f'[Middleware: Client] Attaching Secure Passport for {context.client_id}')
        add_secure_passport(message, context)
        return next_handler(message)

    @staticmethod
    def server_middleware(
        next_handler: Callable[[A2AMessage, CallerContext | None], Any], message: A2AMessage
    ):
        """
        [Conceptual Middleware Layer: Server/Receiving Agent]
        """
        passport = get_secure_passport(message)

        if passport:
            print(
                f'[Middleware: Server] Extracted Secure Passport. Verified: {passport.is_verified}'
            )
        else:
            print('[Middleware: Server] No Secure Passport found or validation failed.')

        return next_handler(message, passport)
