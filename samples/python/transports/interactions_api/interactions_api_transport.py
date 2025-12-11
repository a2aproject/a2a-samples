"""Contains a custom A2A ClientTransport implementation that proxies to the
Gemini Interactions API.
"""

import json
import os

from collections.abc import AsyncGenerator, AsyncIterator
from copy import deepcopy
from typing import Any

import httpx
import httpx_sse

from a2a.client import ClientFactory
from a2a.client.errors import A2AClientError, A2AClientJSONRPCError
from a2a.client.middleware import ClientCallContext
from a2a.client.transports import ClientTransport
from a2a.extensions.common import find_extension_by_uri
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentExtension,
    AgentSkill,
    Artifact,
    ContentTypeNotSupportedError,
    DataPart,
    FilePart,
    FileWithBytes,
    FileWithUri,
    GetTaskPushNotificationConfigParams,
    JSONRPCError,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
    UnsupportedOperationError,
)


class InteractionsApiTransport(ClientTransport):
    """An A2A ClientTransport implementation that converts calls to corresponding Interactions API methods."""

    INTERACTIONS_API_VERSION = 'v1beta'
    EXTENSION_URI = 'https://generativelanguage.googleapis.com/v1beta/a2a'
    TRANSPORT_NAME = 'interactions-api'

    _WELL_KNOWN_AGENTS_NAMES: dict[str, str] = {
        'deep-research-pro-preview-12-2025': 'Deep Research Preview',
    }
    _WELL_KNOWN_AGENT_CONFIG: dict[str, dict[str, Any]] = {
        'deep-research-pro-preview-12-2025': {
            'type': 'deep-research',
            'thinking_summaries': 'auto',
        }
    }
    _WELL_KNOWN_AGENTS_DESCRIPTIONS: dict[str, str] = {
        'deep-research-pro-preview-12-2025': 'Agent powered by Google Deep Research Preview',
    }
    _WELL_KNOWN_AGENTS_SKILLS: dict[str, list[AgentSkill]] = {
        'deep-research-pro-preview-12-2025': [
            AgentSkill(
                id='research',
                name='Deep Research',
                description='In depth research using web searching',
                examples=['What is the best agent development framework?'],
                input_modes=['text/plain'],
                output_modes=['text/plain'],
                tags=['research'],
            )
        ]
    }

    def __init__(self, card: AgentCard, api_key: str | None = None):
        self._card = card
        self._api_key = (
            api_key
            or os.environ.get('GOOGLE_API_KEY')
            or os.environ.get('GEMINI_API_KEY')
        )
        # TODO: Refactor to use GenAI SDK once a release containing Interactions API is available.

        if not self._api_key:
            raise ValueError(
                'API Key not provided and not found in environment variables (GOOGLE_API_KEY or GEMINI_API_KEY).'
            )

        self._base_url = self._card.url
        self._client = httpx.AsyncClient(base_url=self._base_url)
        self._client.headers['x-goog-api-key'] = self._api_key

        # Extract agent_interaction from AgentCard extension
        extension = find_extension_by_uri(self._card, self.EXTENSION_URI)
        if not extension or not extension.params:
            raise ValueError(
                'invalid AgentCard: missing required extension; use make_card to create a correctly formatted AgentCard'
            )
        self._base_request: dict[str, Any] = deepcopy(extension.params)

    @classmethod
    def make_card(
        cls,
        url: str,
        agent: str | None = None,
        model: str | None = None,
        thinking_summaries: bool = True,
        request_opts: dict[str, Any] | None = None,
        agent_card_overrides: dict[str, Any] | None = None,
    ) -> AgentCard:
        """Construct an AgentCard from details of an Interactions API endpoint.

        The resulting AgentCard uses a custom transport, 'interactions-api'. Configure a ClientFactory to understand
        this transport with the InteractionsApiTransport.setup function.

        Args:
            url: URL of the Interactions API endpoint.
            agent: The name of the agent within the endpoint to use.
            model: The name of the model within the endpoint to use.
            thinking_summaries: Whether to enable thinking summary outputs. These are translated to
              TaskStatusUpdateEvents.
            request_opts: Optional dictionary that is used to construct the request object when
              creating an interaction. This allows customizing the parameters passed to the Interactions API,
              such as specifying the generation_config field for model interactions and agent_config field for
              agent interactions. This dictionary is merged into the constructed request object as a last step,
              allowing this object to override fields normally set by the implementation.
            agent_card_overrides: Optional dictionary of values to use when constructing the AgentCard. This allows
              specifying AgentCard fields, such as name, description, or skills. The keys of this dictionary should
              match field names of the AgentCard. The AgentCard is updated as if by calling
              card.model_copy(update=agent_card_overrides).

        Returns:
            An AgentCard that can be used to call the configured Interactions API endpoint.
        """
        # Default AgentCard values
        request = {}
        agent_name: str = ''
        agent_mode = True
        if agent:
            request['agent'] = agent
            agent_name = agent
        elif model:
            if model in cls._WELL_KNOWN_AGENTS_NAMES:
                request['agent'] = model
            else:
                request['model'] = model
                agent_mode = False
            agent_name = model
        else:
            raise ValueError(
                'either agent or model parameter must be specified'
            )
        if thinking_summaries:
            if agent_mode and agent_name in cls._WELL_KNOWN_AGENT_CONFIG:
                request['agent_config'] = cls._WELL_KNOWN_AGENT_CONFIG[agent_name]
            elif not agent_mode:
                request['generation_config'] = {
                    'thinking_summaries': 'auto'
                }
        if request_opts:
            request.update(request_opts)
        card = AgentCard(
            url=url,
            preferred_transport='interactions-api',
            capabilities=AgentCapabilities(
                streaming=True,
                extensions=[
                    AgentExtension(
                        uri=cls.EXTENSION_URI,
                        required=True,
                        params=request,
                    ),
                ],
            ),
            name=cls._WELL_KNOWN_AGENTS_NAMES.get(agent_name, agent_name),
            description=cls._WELL_KNOWN_AGENTS_DESCRIPTIONS.get(
                agent_name, 'Agent powered by Google Interactions API'
            ),
            default_input_modes=['text/plain'],
            default_output_modes=['text/plain'],
            skills=cls._WELL_KNOWN_AGENTS_SKILLS.get(
                agent_name,
                [
                    AgentSkill(
                        id='interact',
                        name='Interact',
                        input_modes=['text/plain'],
                        output_modes=['text/plain'],
                        description='Interact with the agent',
                        examples=['What is 2+2?'],
                        tags=[],
                    )
                ],
            ),
            version='v1beta',
        )

        # Apply overrides
        if agent_card_overrides:
            card = card.model_copy(update=agent_card_overrides)

        return card

    @classmethod
    def setup(cls, client_factory: ClientFactory, api_key: str | None = None):
        """Setup a ClientFactory to support the Interactions API transport.

        Args:
            client_factory: The ClientFactory where support is registered.
            api_key: The Gemini API key to use when calling the Interactions API. If unset, the GOOGLE_API_KEY and
                GEMINI_API_KEY environment variables will be used. If those are unset, a ValueError is raised.
        """
        # Need to access _config to mark the transport supported.
        client_factory._config.supported_transports.append(cls.TRANSPORT_NAME)
        client_factory.register(
            cls.TRANSPORT_NAME,
            lambda card, url, config, interceptors: cls(card, api_key),
        )

    async def send_message(
        self,
        request: MessageSendParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> Task | Message:
        body = _a2a_request_to_interaction(
            request, stream=False, base_request=self._base_request
        )
        response = await self._do_request(
            'POST',
            f'/{self.INTERACTIONS_API_VERSION}/interactions',
            json_data=body,
        )
        return _interaction_to_task(response.json())

    async def send_message_streaming(
        self,
        request: MessageSendParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> AsyncGenerator[
        Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
    ]:
        body = _a2a_request_to_interaction(
            request, stream=True, base_request=self._base_request
        )
        async with httpx_sse.aconnect_sse(
            self._client,
            'POST',
            f'/{self.INTERACTIONS_API_VERSION}/interactions',
            json=body,
            timeout=None,
        ) as event_source:
            await self._translate_response_error(event_source.response)
            stream = event_source.aiter_sse()
            first_event = await anext(stream)
            if first_event.event == 'error':
                raise A2AClientError(first_event.data)
            elif first_event.event != 'interaction.start':
                raise A2AClientError(
                    f'unexpected first event type: {first_event.event}'
                )
            task = _interaction_to_task(first_event.json()['interaction'])
            # Change current state to submitted, since A2A always emits a Task
            # in submitted state first.
            task.status.state = TaskState.submitted
            yield task
            async for event in self._process_stream(stream, task, set()):
                yield event

    async def get_task(
        self,
        request: TaskQueryParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> Task:
        response = await self._do_request(
            'GET', f'/{self.INTERACTIONS_API_VERSION}/interactions/{request.id}'
        )
        return _interaction_to_task(response.json())

    async def cancel_task(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> Task:
        response = await self._do_request(
            'POST',
            f'/{self.INTERACTIONS_API_VERSION}/interactions/{request.id}/cancel',
        )
        return _interaction_to_task(response.json())

    async def set_task_callback(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> TaskPushNotificationConfig:
        raise A2AClientJSONRPCError(
            JSONRPCErrorResponse(
                error=UnsupportedOperationError(
                    message='Push Notifications are not supported by Interactions API transport.'
                )
            )
        )

    async def get_task_callback(
        self,
        request: GetTaskPushNotificationConfigParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> TaskPushNotificationConfig:
        raise A2AClientJSONRPCError(
            JSONRPCErrorResponse(
                error=UnsupportedOperationError(
                    message='Push Notifications are not supported by Interactions API transport.'
                )
            )
        )

    async def resubscribe(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> AsyncGenerator[
        Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
    ]:
        # Resubscribing has two different behaviors: if a model,
        async with httpx_sse.aconnect_sse(
            self._client,
            'GET',
            f'/{self.INTERACTIONS_API_VERSION}/interactions/{request.id}',
            params={'stream': True},
            timeout=None,
        ) as event_source:
            await self._translate_response_error(event_source.response)
            stream = event_source.aiter_sse()
            first_event = await anext(stream)
            if first_event.event == 'error':
                event_data = first_event.json()
                if event_data['error']['code'] == 'not_found':
                    # Models behave differently from agents in the interactions
                    # API. If you attempt to resubscribe to model output that
                    # has completed, you get an error. We can just fetch the
                    # final state of the interaction and yield that.
                    current_task = await self.get_task(
                        TaskQueryParams(id=request.id)
                    )
                    yield current_task
                    return
                # Otherwise raise the error.
                raise A2AClientError(first_event.data)
            if first_event.event == 'interaction.start':
                current_task = _interaction_to_task(
                    first_event.json()['interaction']
                )
                current_task.status.state = TaskState.submitted
                yield current_task
            else:
                raise A2AClientError(
                    f'unexpected first event type: {first_event.event}'
                )
            async for event in self._process_stream(
                stream, current_task, set()
            ):
                yield event

    async def get_card(
        self,
        *,
        context: ClientCallContext | None = None,
        extensions: list[str] | None = None,
    ) -> AgentCard:
        return self._card

    async def close(self) -> None:
        await self._client.aclose()

    async def _do_request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        headers = {'Content-Type': 'application/json'}
        if stream:
            headers['Accept'] = 'text/event-stream'

        if method == 'POST':
            response = await self._client.post(
                path,
                json=json_data,
                params=params,
                headers=headers,
                timeout=None,
            )
        elif method == 'GET':
            response = await self._client.get(
                path, params=params, headers=headers, timeout=None
            )
        else:
            raise ValueError(f'Unsupported HTTP method: {method}')

        await self._translate_response_error(response)
        return response

    async def _translate_response_error(
        self,
        response: httpx.Response,
    ):
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            await e.response.aread()
            if e.response.status_code == 400:
                raise A2AClientJSONRPCError(
                    JSONRPCErrorResponse(
                        error=JSONRPCError(
                            code=-32602,
                            message='Invalid parameters',
                            data=e.response.json(),
                        )
                    )
                ) from e
            if e.response.status_code == 404:
                raise A2AClientJSONRPCError(
                    JSONRPCErrorResponse(
                        error=JSONRPCError(
                            code=-32001,
                            message='Task not found',
                            data=e.response.json(),
                        )
                    )
                ) from e
            if e.response.status_code == 405:
                raise A2AClientJSONRPCError(
                    JSONRPCErrorResponse(
                        error=UnsupportedOperationError(
                            message='Method not supported by Interactions API transport.'
                        )
                    )
                ) from e
            raise A2AClientJSONRPCError(
                JSONRPCErrorResponse(
                    error=JSONRPCError(
                        code=-32603,
                        message='Internal error',
                        data=e.response.json(),
                    )
                )
            ) from e
        except httpx.RequestError as e:
            raise A2AClientJSONRPCError(
                JSONRPCErrorResponse(
                    error=JSONRPCError(
                        code=-32603, message=f'Network or client error: {e}'
                    )
                )
            ) from e

    def _process_event(
        self,
        event: httpx_sse.ServerSentEvent,
        current_task: Task,
        thought_indexes: set,
    ) -> TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None:
        event_type = event.event
        event_data = event.json()
        if event_type == 'interaction.status_update':
            new_state = _interaction_status_to_a2a_task_state(
                event_data['status']
            )
            current_task.status = TaskStatus(state=new_state)
            return TaskStatusUpdateEvent(
                task_id=current_task.id,
                context_id='',
                final=False,
                status=current_task.status,
            )
        if event_type == 'content.start':
            # Depends on content. If not thought, emit ArtifactUpdateEvent with
            # name of "content_{index}". append = True, final = False.
            # If thought, emit TaskStatusUpdateEvent with most recent status and new message.
            # Only if content is set. It may not be.
            if 'content' in event_data:
                # New thought incoming.
                if event_data['content']['type'] == 'thought':
                    thought_indexes.add(event_data['index'])
                    current_task.status.message = Message(
                        message_id=f'output_{event_data["index"]}_0',
                        task_id=current_task.id,
                        role=Role.agent,
                        metadata={'chunk': 0},
                        parts=[],
                    )
        elif event_type == 'content.delta':
            # Emit TaskArtifactUpdatEvent. Otherwise, accumulate
            # message in-memory.
            if event_data['delta']['type'] == 'thought_summary':
                # This should have been setup above.
                current_status_message: Message = current_task.status.message  # type: ignore
                current_status_message.message_id = f'output_{event_data["index"]}_{current_status_message.metadata["chunk"]}'
                current_status_message.metadata['chunk'] += 1
                current_status_message.parts = [
                    _content_to_part(event_data['delta']['content'])
                ]
                return TaskStatusUpdateEvent(
                    task_id=current_task.id,
                    context_id=current_task.context_id,
                    status=current_task.status,
                    final=False,
                )
            if event_data['delta']['type'] == 'thought_signature':
                pass
            else:
                return _content_delta_to_artifact(current_task.id, event_data)

        elif event_type == 'content.stop':
            if event_data['index'] not in thought_indexes:
                return TaskArtifactUpdateEvent(
                    task_id=current_task.id,
                    context_id=current_task.context_id,
                    artifact=Artifact(
                        artifact_id=f'output_{event_data["index"]}',
                        parts=[],
                        name=f'output-{event_data["index"]}',
                    ),
                    last_chunk=True,
                    append=True,
                )
        elif event_type == 'error':
            # Emit TaskStatusUpdateEvent message with error details.
            error = event_data['error']
            current_task.status.message = Message(
                message_id='error',
                role=Role.agent,
                parts=[Part(root=DataPart(data=error))],
            )
            return TaskStatusUpdateEvent(
                task_id=current_task.id,
                context_id=current_task.context_id,
                status=current_task.status,
                final=False,
            )
        elif event_type == 'interaction.complete':
            current_task = _interaction_to_task(event_data['interaction'])
            return TaskStatusUpdateEvent(
                task_id=current_task.id,
                context_id=current_task.context_id,
                status=current_task.status,
                final=True,
            )
        return None

    async def _process_stream(
        self,
        stream: AsyncIterator[httpx_sse.ServerSentEvent],
        current_task: Task,
        thought_indexes: set[int],
    ) -> AsyncGenerator[
        Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
    ]:
        async for event in stream:
            if event.event == 'done':
                return
            if processed := self._process_event(
                event, current_task, thought_indexes
            ):
                yield processed


# Data type converters.


def _part_to_content(part: Part) -> dict[str, Any]:
    """Maps an A2A Part object to an Interactions API Content dictionary."""
    if isinstance(part.root, TextPart):
        content = {'text': part.root.text, 'type': 'text'}
        if part.root.metadata and (
            annotations := part.root.metadata.get('annotations')
        ):
            content['annotations'] = annotations
        return content
    if isinstance(part.root, FilePart):
        mime_type = part.root.file.mime_type
        if not mime_type:
            raise ValueError(
                'FilePart must have a mime_type when using interactions API'
            )
        blob_content = {}

        if isinstance(part.root.file, FileWithBytes):
            blob_content['data'] = part.root.file.bytes
        elif isinstance(part.root.file, FileWithUri):
            blob_content['uri'] = part.root.file.uri

        if part.root.metadata:
            resolution = part.root.metadata.get('resolution')
            if resolution:
                blob_content['resolution'] = resolution

        blob_content['mime_type'] = mime_type
        if mime_type.startswith('image'):
            blob_content['type'] = 'image'
        elif mime_type.startswith('audio'):
            blob_content['type'] = 'audio'
        elif mime_type.startswith('application/pdf'):
            blob_content['type'] = 'document'
        elif mime_type.startswith('video'):
            blob_content['type'] = 'video'
        else:
            raise A2AClientJSONRPCError(
                JSONRPCErrorResponse(
                    error=ContentTypeNotSupportedError(
                        message=f'Unsupported file MIME type for Interactions API mapping: {mime_type}'
                    )
                )
            )
        return blob_content

    if isinstance(part.root, DataPart):
        return {'text': json.dumps(part.root.data), 'type': 'text'}

    raise A2AClientJSONRPCError(
        JSONRPCErrorResponse(
            error=ContentTypeNotSupportedError(
                message=f'Unsupported A2A Part type for Interactions API mapping: {type(part.root)}'
            )
        )
    )


def _a2a_request_to_interaction(
    message_params: MessageSendParams,
    stream: bool,
    base_request: dict[str, Any],
) -> dict[str, Any]:
    """Maps an A2A Message to the input structure for creating an Interaction."""
    message = message_params.message
    request: dict[str, Any] = {
        'input': [_part_to_content(p) for p in message.parts],
        'stream': stream,
        'store': True,
        # Background execution only works for agents
        'background': 'agent' in base_request,
    }
    if message.task_id:
        request['previous_interaction_id'] = message.task_id
    elif message.reference_task_ids:
        request['previous_interaction_id'] = message.reference_task_ids[0]
    if (
        message_params.configuration
        and message_params.configuration.accepted_output_modes
    ):
        modalities = set()
        for mode in message_params.configuration.accepted_output_modes:
            if mode.startswith('text/'):
                modalities.add('text')
            elif mode.startswith('image/'):
                modalities.add('image')
            elif mode.startswith('audio/'):
                modalities.add('audio')
        request['response_modalities'] = list(modalities)
    request.update(base_request)
    return request


def _interaction_status_to_a2a_task_state(status_str: str) -> TaskState:
    """Maps Interactions API status string to A2A TaskState."""
    mapping = {
        'in_progress': TaskState.working,
        'requires_action': TaskState.input_required,
        'completed': TaskState.completed,
        'failed': TaskState.failed,
        'cancelled': TaskState.canceled,
    }
    return mapping.get(status_str, TaskState.unknown)


def _thought_to_messages(index: int, thought: dict[str, Any]) -> list[Message]:
    summaries = thought.get('summary', {}).get('items', [])
    return [Message(
        message_id=f'output_{index}_{i}',
        role=Role.agent,
        parts=[_content_to_part(summary)],
    )  for i, summary in enumerate(summaries)]


def _content_delta_to_artifact(
    task_id: str, event: dict[str, Any]
) -> TaskArtifactUpdateEvent:
    return TaskArtifactUpdateEvent(
        append=True,
        last_chunk=False,
        task_id=task_id,
        context_id='',
        artifact=Artifact(
            artifact_id=f'output_{event["index"]}',
            parts=[_content_to_part(event['delta'])],
            name=f'output-{event["index"]}',
        ),
    )


def _content_to_part(
    content: dict[str, Any],
) -> Part:
    """Maps an Interactions API Content dictionary to an A2A Part object (excluding thoughts)."""
    if content['type'] == 'text':
        md = (
            {'annotations': content.get('annotations')}
            if 'annotations' in content
            else None
        )
        return Part(root=TextPart(text=content['text'], metadata=md))

    for blob_type in ['image', 'audio', 'document', 'video']:
        if content['type'] == blob_type:
            mime_type = content.get('mime_type') or f'{blob_type}/unknown'
            if blob_type == 'document' and not content.get('mime_type'):
                mime_type = 'application/octet-stream'

            metadata = {}
            if 'resolution' in content:
                metadata['resolution'] = content['resolution']

            if 'data' in content:
                return Part(
                    root=FilePart(
                        file=FileWithBytes(
                            bytes=content['data'], mime_type=mime_type
                        ),
                        metadata=metadata if metadata else None,
                    )
                )
            if 'uri' in content:
                return Part(
                    root=FilePart(
                        file=FileWithUri(
                            uri=content['uri'], mime_type=mime_type
                        ),
                        metadata=metadata if metadata else None,
                    )
                )

    return Part(root=DataPart(data={'content': content}))


def _interaction_to_task(interaction: dict[str, Any]) -> Task:
    """Converts a raw Interactions API dictionary response to an A2A Task."""
    task_id = interaction.get('id', '')
    status_str = interaction.get('status', 'UNSPECIFIED')
    task_status_state = _interaction_status_to_a2a_task_state(status_str)

    a2a_history = []

    if 'input' in interaction:
        input_val = interaction['input']
        # Input is either:
        # - Bare string
        # - Content
        # - List of Content
        # - List of Turns
        if isinstance(input_val, list):
            if len(input_val) > 0:
                # Seems unlikely there'd be an empty input list, but...
                if 'role' in input_val[0]:
                    # Turns.
                    for i, turn in enumerate(input_val):
                        part = _content_to_part(turn['content'])
                        role = (
                            Role.user if turn['role'] == 'user' else Role.agent
                        )
                        a2a_history.append(
                            Message(
                                message_id=f'input_{i}', role=role, parts=[part]
                            )
                        )
                else:
                    a2a_history.append(
                        Message(
                            message_id='input_0',
                            role=Role.user,
                            parts=[
                                _content_to_part(content)
                                for content in input_val
                            ],
                        )
                    )
        elif isinstance(input_val, str):
            a2a_history.append(
                Message(
                    message_id='input_0',
                    role=Role.user,
                    parts=[Part(root=TextPart(text=input_val))],
                )
            )
        else:
            a2a_history.append(
                Message(
                    message_id='input_0',
                    role=Role.user,
                    parts=[_content_to_part(input_val)],
                )
            )

    a2a_artifacts = []
    thought_messages = []
    outputs = interaction.get('outputs', [])

    for i, output_content in enumerate(outputs):
        if output_content['type'] == 'thought':
            thought_messages.extend(_thought_to_messages(i, output_content))
        else:
            a2a_part = _content_to_part(output_content)
            a2a_artifacts.append(
                Artifact(
                    artifact_id=f'output_{i}',
                    parts=[a2a_part],
                    name=f'output-{i}',
                )
            )

    # Append thoughts to history
    a2a_history.extend(thought_messages)

    # Determine status message. This isn't quite right: there may be no active
    # status message.
    task_status_message: Message | None = None

    # Error handling overrides thought status
    error_obj = interaction.get('error')
    if error_obj:
        task_status_message = Message(
            message_id='error',
            role=Role.agent,
            parts=[Part(root=TextPart(text=json.dumps(error_obj)))],
        )

    return Task(
        id=task_id,
        context_id='',
        status=TaskStatus(state=task_status_state, message=task_status_message),
        artifacts=a2a_artifacts if a2a_artifacts else None,
        history=a2a_history if a2a_history else None,
    )
