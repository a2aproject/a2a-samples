from typing import Any

import httpx
import jcs
import jwcrypto.common

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentCard,
    AgentExtension,
    Artifact,
    Message,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from jwcrypto import jwk, jws
from pydantic import BaseModel


_URI = 'https://github.com/a2aproject/a2a-samples/samples/extensions/signing/v1'
_FIELD = (
    'github.com/a2aproject/a2a-samples/samples/extensions/signing/v1/signature'
)


class MessageSignature(BaseModel):
    """The type for signatures added to message metadata."""

    agent_url: str
    jws: str


class RemoteAgent(BaseModel):
    """Represents a remote agent that sent a message."""

    agent_card_url: str
    agent_card: AgentCard


class SigningExtensionParams(BaseModel):
    """The type for the params field of the signing extension."""

    jwk: dict[str, Any]


class _DelegateAgentExecutor(AgentExecutor):
    """An implementation of an AgentExecutor that proxies all methods to a delegate."""

    def __init__(self, delegate: AgentExecutor):
        self._delegate = delegate

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        return await self._delegate.execute(context, event_queue)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        return await self._delegate.cancel(context, event_queue)


class NopMessageSigner:
    """A message signer that does not sign messages."""

    def sign(self, message: Message | Artifact | None):
        """Doesn't sign the provided message."""
        return


class JwkMessageSigner:
    """A utility class for adding signatures to messages."""

    def __init__(self, key: jwk.JWK, agent_url: str):
        self._key = key
        self._agent_url = agent_url

    def sign(self, message: Message | Artifact | None) -> None:
        """Add a signature to the provided message or artifact."""
        if message:
            sign_message(message, self._key, self._agent_url)


MessageSigner = NopMessageSigner | JwkMessageSigner


class EventSigner:
    """A helper for signing events, which contain messages."""

    def __init__(self, message_signer: MessageSigner):
        self._signer = message_signer

    def sign(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        """Sign the content contained within an event."""
        if isinstance(event, Message):
            self._signer.sign(event)
        elif isinstance(event, Task):
            for a in event.artifacts or []:
                self._signer.sign(a)
            for m in event.history or []:
                if m.role == Role.agent:
                    self._signer.sign(m)
            self._signer.sign(event.status.message)
        elif isinstance(event, TaskStatusUpdateEvent):
            self._signer.sign(event.status.message)
        elif isinstance(event, TaskArtifactUpdateEvent):
            self._signer.sign(event.artifact)


class SigningEventQueue(EventQueue):
    """A decorator class that signs outgoing events."""

    def __init__(self, delegate: EventQueue, signer: EventSigner):
        # Note: explicitly does not call super init since all methods call
        # the supplied delegate.
        self._delegate = delegate
        self._signer = signer

    async def enqueue_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        # Sign the event, then publish it to the delegate.
        self._signer.sign(event)
        await self._delegate.enqueue_event(event)

    async def dequeue_event(
        self, no_wait: bool = False
    ) -> Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent:
        return await self._delegate.dequeue_event(no_wait)

    def tap(self) -> EventQueue:
        return self._delegate.tap()

    async def close(self) -> None:
        await self._delegate.close()

    def is_closed(self) -> bool:
        return self._delegate.is_closed()

    def task_done(self) -> None:
        return self._delegate.task_done()


class SigningAgentExecutor(_DelegateAgentExecutor):
    """An AgentExecutor wrapper that automatically signs messages/artifacts."""

    def __init__(self, delegate: AgentExecutor, ext: 'SigningExtension'):
        super().__init__(delegate)
        self._ext = ext

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        # Call the base delegate implementation, but with a wrapped queue.
        return await super().execute(
            context,
            SigningEventQueue(
                event_queue,
                EventSigner(self._ext.get_message_signer(context)),
            ),
        )


class SigningExtension:
    """Class for the message signing extension."""

    def __init__(self, signing_key: jwk.JWK, card_url: str):
        self.signing_key = signing_key
        self.card_url = card_url

    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing the support for signing."""
        return AgentExtension(
            uri=_URI,
            description='Supports verifying incoming message signatures and attaching signatures to messages',
            params=SigningExtensionParams(
                jwk=self.signing_key.export_public(as_dict=True),
            ).model_dump(),
        )

    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap the AgentExecutor with automatic message signing."""
        return SigningAgentExecutor(executor, self)

    def is_active(self, request_context: RequestContext) -> bool:
        """Returns whether this extension is active for the given request."""
        return _URI in request_context.requested_extensions

    def get_message_signer(
        self, request_context: RequestContext
    ) -> MessageSigner:
        """Returns a MessageSigner used for signing messages for a request."""
        if self.is_active(request_context):
            # Note: if we retrieve a message signer, the extension is active.
            # If the agent never retrieves the signer, it can't add signatures.
            # Therefore, this is a good place to indicate that the extension is
            # active.
            request_context.add_activated_extension(_URI)
            return JwkMessageSigner(self.signing_key, self.card_url)
        return NopMessageSigner()

    async def get_agent_author(
        self, client: httpx.AsyncClient, message: Message
    ) -> RemoteAgent | None:
        """Retrieve the verified author of a message, if the message is signed.

        Raises an error if a signature is present but verification fails.
        """
        return await get_agent_author(client, message)


class SignatureValidationError(Exception):
    """Raised when a message signature was present but could not be validated."""


async def get_agent_author(
    client: httpx.AsyncClient, message: Message | None
) -> RemoteAgent | None:
    """Retrieve the details of the agent author, if present."""
    if not message:
        return None
    if not message.metadata or not (sig := message.metadata.get(_FIELD)):
        return None
    signature = MessageSignature.model_validate(sig)
    parsed_jws = jws.JWS.from_jose_token(signature.jws)
    # Fetch the AgentCard for the asserted agent identity.
    response = await client.get(signature.agent_url)
    remote_agent_card = AgentCard.model_validate_json(
        response.raise_for_status().content
    )
    if not (ext := get_signing_ext(remote_agent_card)):
        raise SignatureValidationError(
            'remote agent card has no signing extension'
        )
    remote_params = SigningExtensionParams.model_validate(ext.params)
    # Load the signing key asserted by the agent.
    remote_jwk = jwk.JWK()
    remote_jwk.import_key(**remote_params.jwk)
    signing_payload = get_message_signing_payload(message)
    # Verify the signature on the message.
    parsed_jws.verify(remote_jwk, detached_payload=signing_payload)
    # If all good, we've authenticated the remote agent.
    return RemoteAgent(
        agent_card=remote_agent_card, agent_card_url=signature.agent_url
    )


def sign_message(
    message: Message | Artifact, signing_key: jwk.JWK, agent_id: str
):
    """Sign the given message using the supplied key, asserting the given Agent ID."""
    signing_payload = get_message_signing_payload(message)
    sig_jws = jws.JWS(signing_payload)
    sig_jws.add_signature(signing_key, alg='ES256')
    sig_jws.detach_payload()
    serialized_jws = sig_jws.serialize(compact=True)
    message_sig = MessageSignature(agent_url=agent_id, jws=serialized_jws)
    if not message.metadata:
        message.metadata = {}
    message.metadata[_FIELD] = message_sig.model_dump()


def get_message_signing_payload(message: Message | Artifact) -> str:
    """Given a Message, return the canonicalized payload for signing that message."""
    cleaned_message = message.model_copy(deep=True)
    # Remove the signature, if present.
    if cleaned_message.metadata and cleaned_message.metadata.get(_FIELD):
        cleaned_message.metadata.pop(_FIELD)
    unencoded_data = jcs.canonicalize(cleaned_message.model_dump())
    return jwcrypto.common.base64url_encode(unencoded_data)


def get_signing_ext(card: AgentCard) -> AgentExtension | None:
    """Retrieves the signing extension from the AgentCard."""
    for ext in card.capabilities.extensions or []:
        if ext.uri == _URI:
            return ext

    return None
