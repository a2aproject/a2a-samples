import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import httpx
import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentExtension,
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from jwcrypto import jwk, jws

from a2a_signing_ext import signing


@pytest.fixture
def test_key() -> jwk.JWK:
    """Returns a new JWK for testing."""
    return jwk.JWK.generate(kty='EC', crv='P-256')


@pytest.fixture
def test_agent_url() -> str:
    """Returns a test agent URL."""
    return 'http://test.agent.com'


@pytest.fixture
def test_message() -> Message:
    """Returns a simple test message."""
    return Message(
        messageId='test-message',
        role=Role.user,
        parts=[Part(TextPart(text='Hello'))],
    )


@pytest.fixture
def test_artifact() -> Artifact:
    """Returns a simple test artifact."""
    return Artifact(
        artifactId='test-artifact',
        parts=[Part(TextPart(text='Some artifact content'))],
    )


class TestGetSigningExt:
    def test_returns_extension_if_present(self):
        signing_ext = signing.SigningExtension(
            jwk.JWK.generate(kty='EC'), 'https://example.com/test'
        )
        agent_ext = signing_ext.agent_extension()
        card = AgentCard(
            capabilities=AgentCapabilities(extensions=[agent_ext]),
            name='Test Agent',
            description='A test agent',
            defaultInputModes=[],
            defaultOutputModes=[],
            skills=[],
            url='http://test.com',
            version='1.0',
        )
        assert signing.get_signing_ext(card) == agent_ext

    def test_returns_none_if_not_present(self):
        other_ext = AgentExtension(uri='other_uri', description='test')
        card = AgentCard(
            capabilities=AgentCapabilities(extensions=[other_ext]),
            name='Test Agent',
            description='A test agent',
            defaultInputModes=[],
            defaultOutputModes=[],
            skills=[],
            url='http://test.com',
            version='1.0',
        )
        assert signing.get_signing_ext(card) is None

    def test_returns_none_if_no_extensions(self):
        card = AgentCard(
            capabilities=AgentCapabilities(),
            name='Test Agent',
            description='A test agent',
            defaultInputModes=[],
            defaultOutputModes=[],
            skills=[],
            url='http://test.com',
            version='1.0',
        )
        assert signing.get_signing_ext(card) is None


class TestGetMessageSigningPayload:
    def test_creates_canonical_payload(self, test_message: Message):
        payload = signing.get_message_signing_payload(test_message)
        assert isinstance(payload, str)

    def test_removes_signature_before_canonicalization(
        self, test_message: Message
    ):
        message_with_sig = test_message.model_copy(deep=True)
        message_with_sig.metadata = {signing._FIELD: 'some_signature'}

        payload_with_sig = signing.get_message_signing_payload(message_with_sig)

        # Create a new clean message for comparison
        clean_message = test_message.model_copy(deep=True)
        if clean_message.metadata:
            clean_message.metadata.pop(signing._FIELD, None)
        payload_without_sig = signing.get_message_signing_payload(clean_message)

        assert payload_with_sig == payload_without_sig


class TestSignMessage:
    def test_adds_signature_to_metadata(
        self, test_message: Message, test_key: jwk.JWK, test_agent_url: str
    ):
        clean_message = test_message.model_copy(deep=True)
        assert clean_message.metadata is None
        signing.sign_message(clean_message, test_key, test_agent_url)
        assert clean_message.metadata is not None
        assert signing._FIELD in clean_message.metadata

        sig_data = signing.MessageSignature.model_validate(
            clean_message.metadata[signing._FIELD]
        )
        assert sig_data.agent_url == test_agent_url

        # Verify signature
        parsed_jws = jws.JWS.from_jose_token(sig_data.jws)
        payload = signing.get_message_signing_payload(clean_message)
        parsed_jws.verify(test_key, detached_payload=payload)


class TestJwkMessageSigner:
    def test_sign_adds_signature(
        self, test_message: Message, test_key: jwk.JWK, test_agent_url: str
    ):
        signer = signing.JwkMessageSigner(test_key, test_agent_url)
        signer.sign(test_message)
        assert test_message.metadata is not None
        assert signing._FIELD in test_message.metadata

    def test_sign_does_nothing_for_none(
        self, test_key: jwk.JWK, test_agent_url: str
    ):
        signer = signing.JwkMessageSigner(test_key, test_agent_url)
        signer.sign(None)  # Should not raise


class TestNopMessageSigner:
    def test_sign_does_nothing(self, test_message: Message):
        signer = signing.NopMessageSigner()
        signer.sign(test_message)
        assert test_message.metadata is None


class TestEventSigner:
    @pytest.fixture
    def mock_signer(self) -> Mock:
        return Mock(spec=signing.JwkMessageSigner)

    @pytest.fixture
    def event_signer(self, mock_signer: Mock) -> signing.EventSigner:
        return signing.EventSigner(mock_signer)

    def test_sign_message(
        self,
        event_signer: signing.EventSigner,
        mock_signer: Mock,
        test_message: Message,
    ):
        event_signer.sign(test_message)
        mock_signer.sign.assert_called_once_with(test_message)

    def test_sign_task(
        self, event_signer: signing.EventSigner, mock_signer: Mock
    ):
        task = Task(
            id='1',
            status=TaskStatus(
                state=TaskState.working,
                message=Message(
                    messageId='m1',
                    role=Role.agent,
                    parts=[Part(TextPart(text='working'))],
                ),
            ),
            history=[
                Message(
                    messageId='m2',
                    role=Role.user,
                    parts=[Part(TextPart(text='do it'))],
                ),
                Message(
                    messageId='m3',
                    role=Role.agent,
                    parts=[Part(TextPart(text='ok'))],
                ),
            ],
            artifacts=[
                Artifact(
                    artifactId='a1', parts=[Part(TextPart(text='artifact1'))]
                )
            ],
            contextId='c1',
        )
        event_signer.sign(task)
        assert mock_signer.sign.call_count == 3
        mock_signer.sign.assert_any_call(task.artifacts[0])
        mock_signer.sign.assert_any_call(task.history[1])  # only agent messages
        mock_signer.sign.assert_any_call(task.status.message)

    def test_sign_task_status_update(
        self, event_signer: signing.EventSigner, mock_signer: Mock
    ):
        event = TaskStatusUpdateEvent(
            taskId='1',
            status=TaskStatus(
                state=TaskState.completed,
                message=Message(
                    messageId='m1',
                    role=Role.agent,
                    parts=[Part(TextPart(text='done'))],
                ),
            ),
            contextId='c1',
            final=True,
        )
        event_signer.sign(event)
        mock_signer.sign.assert_called_once_with(event.status.message)

    def test_sign_task_artifact_update(
        self, event_signer: signing.EventSigner, mock_signer: Mock
    ):
        event = TaskArtifactUpdateEvent(
            taskId='1',
            artifact=Artifact(
                artifactId='a1', parts=[Part(TextPart(text='new artifact'))]
            ),
            contextId='c1',
        )
        event_signer.sign(event)
        mock_signer.sign.assert_called_once_with(event.artifact)


class TestSigningEventQueue:
    @pytest.fixture
    def mock_delegate(self) -> MagicMock:
        # MagicMock can handle both sync and async methods
        return MagicMock(spec=EventQueue)

    @pytest.fixture
    def mock_signer(self) -> Mock:
        return Mock(spec=signing.EventSigner)

    @pytest.fixture
    def queue(
        self, mock_delegate: MagicMock, mock_signer: Mock
    ) -> signing.SigningEventQueue:
        return signing.SigningEventQueue(mock_delegate, mock_signer)

    @pytest.mark.asyncio
    async def test_enqueue_event_signs_first(
        self,
        queue: signing.SigningEventQueue,
        mock_delegate: MagicMock,
        mock_signer: Mock,
        test_message: Message,
    ):
        mock_delegate.enqueue_event = AsyncMock()

        await queue.enqueue_event(test_message)

        mock_signer.sign.assert_called_once_with(test_message)
        mock_delegate.enqueue_event.assert_awaited_once_with(test_message)

    @pytest.mark.asyncio
    async def test_dequeue_event_proxies_call(
        self, queue: signing.SigningEventQueue, mock_delegate: MagicMock
    ):
        mock_delegate.dequeue_event = AsyncMock(return_value='event')
        result = await queue.dequeue_event(no_wait=True)
        mock_delegate.dequeue_event.assert_awaited_once_with(no_wait=True)
        assert result == 'event'

    def test_tap_proxies_call(
        self, queue: signing.SigningEventQueue, mock_delegate: MagicMock
    ):
        queue.tap()
        mock_delegate.tap.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_proxies_call(
        self, queue: signing.SigningEventQueue, mock_delegate: MagicMock
    ):
        mock_delegate.close = AsyncMock()
        await queue.close()
        mock_delegate.close.assert_awaited_once()

    def test_is_closed_proxies_call(
        self, queue: signing.SigningEventQueue, mock_delegate: MagicMock
    ):
        queue.is_closed()
        mock_delegate.is_closed.assert_called_once()

    def test_task_done_proxies_call(
        self, queue: signing.SigningEventQueue, mock_delegate: MagicMock
    ):
        queue.task_done()
        mock_delegate.task_done.assert_called_once()


@pytest.mark.asyncio
class TestGetAgentAuthor:
    @pytest.fixture
    def remote_key(self) -> jwk.JWK:
        return jwk.JWK.generate(kty='EC', crv='P-256')

    @pytest.fixture
    def remote_agent_card(self, remote_key: jwk.JWK) -> AgentCard:
        return AgentCard(
            agent_id='remote_agent',
            name='Remote Agent',
            description='A remote test agent',
            capabilities=AgentCapabilities(
                extensions=[
                    AgentExtension(
                        uri=signing._URI,
                        description='signing',
                        params=signing.SigningExtensionParams(
                            jwk=remote_key.export_public(as_dict=True)
                        ).model_dump(),
                    )
                ]
            ),
            defaultInputModes=[],
            defaultOutputModes=[],
            skills=[],
            url='http://test.com',
            version='1.0',
        )

    @pytest.fixture
    def signed_message(
        self, test_message: Message, remote_key: jwk.JWK, test_agent_url: str
    ) -> Message:
        msg = test_message.model_copy(deep=True)
        signing.sign_message(msg, remote_key, test_agent_url)
        return msg

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        return AsyncMock(spec=httpx.AsyncClient)

    async def test_returns_none_for_none_message(self, mock_client: AsyncMock):
        assert await signing.get_agent_author(mock_client, None) is None

    async def test_returns_none_for_unsigned_message(
        self, mock_client: AsyncMock, test_message: Message
    ):
        assert await signing.get_agent_author(mock_client, test_message) is None

    async def test_successful_verification(
        self,
        mock_client: AsyncMock,
        signed_message: Message,
        remote_agent_card: AgentCard,
        test_agent_url: str,
    ):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.raise_for_status.return_value = None
        mock_response.content = remote_agent_card.model_dump_json()
        mock_client.get.return_value = mock_response

        author = await signing.get_agent_author(mock_client, signed_message)

        mock_client.get.assert_awaited_once_with(test_agent_url)
        assert author is not None
        assert author.agent_card_url == test_agent_url
        assert author.agent_card == remote_agent_card

    async def test_raises_on_http_error(
        self, mock_client: AsyncMock, signed_message: Message
    ):
        mock_client.get.side_effect = httpx.RequestError('test error')
        with pytest.raises(httpx.RequestError):
            await signing.get_agent_author(mock_client, signed_message)

    async def test_raises_on_verification_error(
        self,
        mock_client: AsyncMock,
        signed_message: Message,
        remote_agent_card: AgentCard,
    ):
        # Tamper with the signature
        sig_data = signed_message.metadata[signing._FIELD]
        sig_data['jws'] += 'tampered'

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.raise_for_status.return_value = None
        mock_response.content = remote_agent_card.model_dump_json()
        mock_client.get.return_value = mock_response

        with pytest.raises(jws.InvalidJWSSignature):
            await signing.get_agent_author(mock_client, signed_message)

    async def test_raises_if_remote_card_has_no_signing_ext(
        self,
        mock_client: AsyncMock,
        signed_message: Message,
        remote_agent_card: AgentCard,
    ):
        remote_agent_card.capabilities.extensions = []  # Remove extension
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.raise_for_status.return_value = None
        mock_response.content = remote_agent_card.model_dump_json()
        mock_client.get.return_value = mock_response

        with pytest.raises(
            signing.SignatureValidationError,
            match='remote agent card has no signing extension',
        ):
            await signing.get_agent_author(mock_client, signed_message)


class TestSigningExtension:
    @pytest.fixture
    def extension(
        self, test_key: jwk.JWK, test_agent_url: str
    ) -> signing.SigningExtension:
        return signing.SigningExtension(test_key, test_agent_url)

    def test_agent_extension(
        self, extension: signing.SigningExtension, test_key: jwk.JWK
    ):
        ext = extension.agent_extension()
        assert ext.uri == signing._URI
        assert ext.description is not None
        params = signing.SigningExtensionParams.model_validate(ext.params)
        assert params.jwk == test_key.export_public(as_dict=True)

    def test_wrap_executor(self, extension: signing.SigningExtension):
        mock_executor = Mock()
        wrapped = extension.wrap_executor(mock_executor)
        assert isinstance(wrapped, signing.SigningAgentExecutor)
        assert wrapped._delegate == mock_executor
        assert wrapped._ext == extension

    def test_is_active(self, extension: signing.SigningExtension):
        context = RequestContext(requested_extensions=[signing._URI])
        assert extension.is_active(context)
        context.requested_extensions = ['other_uri']
        assert not extension.is_active(context)

    def test_get_message_signer_active(
        self, extension: signing.SigningExtension, test_key, test_agent_url
    ):
        context = RequestContext(requested_extensions=[signing._URI])
        signer = extension.get_message_signer(context)
        assert isinstance(signer, signing.JwkMessageSigner)
        assert signer._key == test_key
        assert signer._agent_url == test_agent_url
        assert signing._URI in context.activated_extensions

    def test_get_message_signer_inactive(
        self, extension: signing.SigningExtension
    ):
        context = RequestContext(requested_extensions=[])
        signer = extension.get_message_signer(context)
        assert isinstance(signer, signing.NopMessageSigner)
        assert signing._URI not in context.activated_extensions

    @pytest.mark.asyncio
    async def test_get_agent_author(self, extension: signing.SigningExtension):
        with patch(
            'a2a_signing_ext.signing.get_agent_author',
            new_callable=AsyncMock,
        ) as mock_get:
            mock_client = AsyncMock()
            mock_message = Mock()
            await extension.get_agent_author(mock_client, mock_message)
            mock_get.assert_awaited_once_with(mock_client, mock_message)
