"""A small A2A-to-A2A connector for a remote Evidence Bench service."""

from __future__ import annotations

import json

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    Artifact,
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskState,
)
from a2a.utils.errors import TaskNotCancelableError
from google.protobuf.json_format import MessageToDict, ParseDict


if TYPE_CHECKING:
    from a2a.server.events import EventQueue


ALLOWED_MCP_SERVERS = {'brave-search', 'chrome-devtools', 'context7'}
DEFAULT_MCP_SERVERS = ('context7', 'brave-search', 'chrome-devtools')
ALLOWED_ARTIFACTS = {'report.md', 'run-summary.json'}
MAX_PARTS = 16
MAX_TEXT_BYTES = 64 * 1024
MAX_RAW_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_RAW_BYTES = 16 * 1024 * 1024
MAX_REPORT_BYTES = 1024 * 1024
MAX_SUMMARY_BYTES = 128 * 1024
TERMINAL_STATES = {
    TaskState.TASK_STATE_COMPLETED,
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_CANCELED,
    TaskState.TASK_STATE_REJECTED,
    TaskState.TASK_STATE_INPUT_REQUIRED,
    TaskState.TASK_STATE_AUTH_REQUIRED,
}


class ConnectorError(RuntimeError):
    """A safe, non-secret connector failure."""


@dataclass(frozen=True)
class RemoteRunResult:
    """Terminal state and bounded candidate artifacts returned by Evidence Bench."""

    state: int
    artifacts: dict[str, Artifact]


class RemoteRunner(Protocol):
    """Injectable remote boundary used by the connector executor."""

    @abstractmethod
    async def run(self, message: Message) -> RemoteRunResult:
        """Delegate one sanitized message to Evidence Bench."""
        raise NotImplementedError


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ConnectorError('Evidence Bench URL must be absolute HTTP(S).')
    if parsed.username or parsed.password:
        raise ConnectorError('Evidence Bench URL must not contain credentials.')
    default_port = 443 if parsed.scheme == 'https' else 80
    return parsed.scheme, parsed.hostname.lower(), parsed.port or default_port


def _remote_jsonrpc_interface(card: AgentCard, base_url: str) -> str:
    expected_origin = _origin(base_url)
    for interface in card.supported_interfaces:
        if interface.protocol_binding.upper() == 'JSONRPC' and interface.protocol_version == '1.0':
            if _origin(interface.url) != expected_origin:
                raise ConnectorError('Evidence Bench Agent Card moved JSON-RPC to another origin.')
            return interface.url
    raise ConnectorError('Evidence Bench does not advertise JSON-RPC A2A 1.0.')


class EvidenceBenchRemoteRunner:
    """Delegate through the official A2A client without exposing its bearer token."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = 2700,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout_seconds = timeout_seconds
        _origin(self.base_url)
        if not token:
            raise ConnectorError('EVIDENCE_BENCH_A2A_TOKEN is required.')
        if timeout_seconds <= 0:
            raise ConnectorError('Evidence Bench timeout must be positive.')

    async def run(self, message: Message) -> RemoteRunResult:
        """Send one message and retain only the final state and named artifacts."""
        timeout = httpx.Timeout(
            self.timeout_seconds,
            connect=min(30.0, self.timeout_seconds),
        )
        headers = {
            'A2A-Version': '1.0',
            'Authorization': f'Bearer {self.token}',
        }
        client = None
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as http_client:
                card = await A2ACardResolver(
                    httpx_client=http_client,
                    base_url=self.base_url,
                ).get_agent_card()
                _remote_jsonrpc_interface(card, self.base_url)
                client = await create_client(
                    agent=card,
                    client_config=ClientConfig(
                        streaming=True,
                        httpx_client=http_client,
                        accepted_output_modes=['application/json', 'text/markdown'],
                    ),
                )
                request = SendMessageRequest(
                    message=message,
                    configuration=SendMessageConfiguration(
                        accepted_output_modes=['application/json', 'text/markdown']
                    ),
                )
                state = TaskState.TASK_STATE_UNSPECIFIED
                artifacts: dict[str, Artifact] = {}
                async for response in client.send_message(request):
                    payload = response.WhichOneof('payload')
                    if payload == 'task':
                        state = response.task.status.state
                        for artifact in response.task.artifacts:
                            _remember_artifact(artifacts, artifact)
                    elif payload == 'status_update':
                        state = response.status_update.status.state
                    elif payload == 'artifact_update':
                        _remember_artifact(
                            artifacts,
                            response.artifact_update.artifact,
                        )
                _require_terminal_state(state)
                return RemoteRunResult(state=state, artifacts=artifacts)
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError('Evidence Bench A2A request failed.') from exc
        finally:
            if client is not None:
                await client.close()


def _remember_artifact(artifacts: dict[str, Artifact], artifact: Artifact) -> None:
    if artifact.name not in ALLOWED_ARTIFACTS:
        return
    copied = Artifact()
    copied.CopyFrom(artifact)
    artifacts[artifact.name] = copied


def _require_terminal_state(state: int) -> None:
    if state not in TERMINAL_STATES:
        raise ConnectorError('Evidence Bench did not return a terminal A2A task state.')


def _sanitize_parts(parts: list[Part]) -> list[Part]:
    if not 1 <= len(parts) <= MAX_PARTS:
        raise ValueError(f'Messages must contain between 1 and {MAX_PARTS} parts.')
    text_bytes = 0
    raw_bytes = 0
    has_objective = False
    sanitized = []
    for part in parts:
        content = part.WhichOneof('content')
        if content == 'text':
            encoded = part.text.encode('utf-8')
            text_bytes += len(encoded)
            has_objective = has_objective or bool(part.text.strip())
            clean = Part(text=part.text, media_type=part.media_type or 'text/plain')
        elif content == 'raw':
            if (
                not part.filename
                or part.filename in {'.', '..'}
                or '/' in part.filename
                or '\\' in part.filename
                or '\x00' in part.filename
            ):
                raise ValueError('Raw file parts require a safe basename.')
            if len(part.raw) > MAX_RAW_FILE_BYTES:
                raise ValueError('One raw file part exceeds the connector size limit.')
            raw_bytes += len(part.raw)
            clean = Part(
                raw=part.raw,
                filename=part.filename,
                media_type=part.media_type or 'application/octet-stream',
            )
        else:
            raise ValueError('Only text and raw file parts can be delegated.')
        sanitized.append(clean)

    if not has_objective:
        raise ValueError('A non-empty text objective is required.')
    if text_bytes > MAX_TEXT_BYTES:
        raise ValueError('Message text exceeds the connector size limit.')
    if raw_bytes > MAX_TOTAL_RAW_BYTES:
        raise ValueError('Raw file parts exceed the connector total size limit.')
    return sanitized


def _sanitize_metadata(message: Message) -> dict[str, object]:
    metadata = MessageToDict(message.metadata) if message.HasField('metadata') else {}
    unknown = set(metadata) - {'enable_code', 'mcp_servers'}
    if unknown:
        raise ValueError(f'Unsupported message metadata: {", ".join(sorted(unknown))}.')
    enable_code = metadata.get('enable_code', False)
    mcp_servers = metadata.get('mcp_servers', list(DEFAULT_MCP_SERVERS))
    if not isinstance(enable_code, bool):
        raise TypeError('metadata.enable_code must be a boolean.')
    if not isinstance(mcp_servers, list) or any(not isinstance(item, str) for item in mcp_servers):
        raise TypeError('metadata.mcp_servers must be a list of strings.')
    invalid = set(mcp_servers) - ALLOWED_MCP_SERVERS
    if invalid:
        raise ValueError(f'Unsupported MCP servers: {", ".join(sorted(invalid))}.')
    return {
        'enable_code': enable_code,
        'mcp_servers': list(dict.fromkeys(mcp_servers)),
    }


def sanitize_message(message: Message, context_id: str) -> Message:
    """Copy only bounded text/raw inputs and explicitly allow-listed metadata."""
    if message.role != Role.ROLE_USER:
        raise ValueError('Only user messages can be delegated.')
    forwarded = Message(
        message_id=str(uuid4()),
        context_id=context_id,
        role=Role.ROLE_USER,
        parts=_sanitize_parts(list(message.parts)),
    )
    ParseDict(_sanitize_metadata(message), forwarded.metadata)
    return forwarded


def bounded_output_parts(artifact: Artifact) -> list[Part]:
    """Convert one expected remote artifact into bounded, metadata-free parts."""
    if artifact.name == 'report.md':
        if not artifact.parts or any(
            part.WhichOneof('content') != 'text' for part in artifact.parts
        ):
            raise ConnectorError('Evidence Bench report.md is not text.')
        report = ''.join(part.text for part in artifact.parts)
        if len(report.encode('utf-8')) > MAX_REPORT_BYTES:
            raise ConnectorError('Evidence Bench report.md exceeds the size limit.')
        return [new_text_part(report, media_type='text/markdown')]

    if artifact.name == 'run-summary.json':
        if len(artifact.parts) != 1 or artifact.parts[0].WhichOneof('content') != 'data':
            raise ConnectorError('Evidence Bench run-summary.json is not structured data.')
        summary = MessageToDict(artifact.parts[0].data)
        if not isinstance(summary, dict):
            raise ConnectorError('Evidence Bench run-summary.json must be an object.')
        encoded = json.dumps(summary, separators=(',', ':'), sort_keys=True).encode()
        if len(encoded) > MAX_SUMMARY_BYTES:
            raise ConnectorError('Evidence Bench run-summary.json exceeds the size limit.')
        return [new_data_part(summary, media_type='application/json')]

    raise ConnectorError('Evidence Bench returned an unsupported artifact.')


def _require_expected_artifacts(result: RemoteRunResult) -> None:
    if set(result.artifacts) != ALLOWED_ARTIFACTS:
        raise ConnectorError('Evidence Bench completed without both expected artifacts.')


class EvidenceBenchConnectorExecutor(AgentExecutor):
    """Expose a bounded local A2A task backed by remote Evidence Bench execution."""

    def __init__(self, remote: RemoteRunner) -> None:
        self.remote = remote

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Delegate a validated request and emit only bounded terminal artifacts."""
        if context.message is None or not context.task_id or not context.context_id:
            raise ValueError('A2A message, task ID, and context ID are required.')
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            forwarded = sanitize_message(context.message, context.context_id)
        except (TypeError, ValueError) as exc:
            await updater.reject(new_text_message(str(exc)))
            return

        await updater.start_work(new_text_message('Delegating to Evidence Bench.'))
        try:
            result = await self.remote.run(forwarded)
            if result.state == TaskState.TASK_STATE_COMPLETED:
                _require_expected_artifacts(result)
                for name in ('run-summary.json', 'report.md'):
                    await updater.add_artifact(
                        bounded_output_parts(result.artifacts[name]),
                        name=name,
                    )
                await updater.complete(new_text_message('Evidence Bench completed.'))
            elif result.state == TaskState.TASK_STATE_REJECTED:
                await updater.reject(new_text_message('Evidence Bench rejected the task.'))
            elif result.state == TaskState.TASK_STATE_CANCELED:
                await updater.cancel(new_text_message('Evidence Bench canceled the task.'))
            else:
                await updater.failed(new_text_message('Evidence Bench did not complete the task.'))
        except ConnectorError:
            await updater.failed(new_text_message('Evidence Bench delegation failed.'))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Keep the initial sample simple; remote cancellation is not proxied."""
        del context, event_queue
        raise TaskNotCancelableError(
            message='The Evidence Bench connector does not proxy cancellation.'
        )
