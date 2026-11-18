# ruff: noqa: PLR2004, S101, SLF001

import asyncio
import base64
import json

from dataclasses import dataclass, field

import pytest

from a2a.helpers import new_data_part, new_text_part
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    Artifact,
    Message,
    Part,
    Role,
    StreamResponse,
    Task,
    TaskState,
    TaskStatus,
)
from google.protobuf.json_format import MessageToDict, ParseDict
from starlette.testclient import TestClient

import evidence_bench_connector.agent_executor as connector

from evidence_bench_connector.agent_executor import (
    ConnectorError,
    EvidenceBenchRemoteRunner,
    RemoteRunResult,
    bounded_output_parts,
    sanitize_message,
)
from evidence_bench_connector.server import build_agent_card, create_app


def _artifact(name: str) -> Artifact:
    if name == 'report.md':
        return Artifact(
            artifact_id='report',
            name=name,
            parts=[new_text_part('# Results\n\nA bounded report.', 'text/markdown')],
        )
    return Artifact(
        artifact_id='summary',
        name=name,
        parts=[new_data_part({'status': 'supported'}, 'application/json')],
    )


@dataclass
class FakeRemote:
    state: int = TaskState.TASK_STATE_COMPLETED
    artifacts: dict[str, Artifact] = field(
        default_factory=lambda: {
            'report.md': _artifact('report.md'),
            'run-summary.json': _artifact('run-summary.json'),
        }
    )
    messages: list[Message] = field(default_factory=list)

    async def run(self, message: Message) -> RemoteRunResult:
        copied = Message()
        copied.CopyFrom(message)
        self.messages.append(copied)
        return RemoteRunResult(self.state, self.artifacts)


def _stream(client: TestClient, message: dict) -> list[dict]:
    with client.stream(
        'POST',
        '/',
        headers={'A2A-Version': '1.0', 'Accept': 'text/event-stream'},
        json={
            'jsonrpc': '2.0',
            'id': 'connector-test',
            'method': 'SendStreamingMessage',
            'params': {'message': message, 'configuration': {}},
        },
    ) as response:
        assert response.status_code == 200, response.text
        return [
            json.loads(line.removeprefix('data: '))
            for line in response.iter_lines()
            if line.startswith('data: ')
        ]


def _states_and_artifacts(events: list[dict]) -> tuple[list[str], set[str]]:
    states = []
    artifacts = set()
    for event in events:
        result = event['result']
        if 'task' in result:
            states.append(result['task']['status']['state'])
        if 'statusUpdate' in result:
            states.append(result['statusUpdate']['status']['state'])
        if 'artifactUpdate' in result:
            artifacts.add(result['artifactUpdate']['artifact']['name'])
    return states, artifacts


def test_agent_card_and_successful_delegation_are_a2a_1_0() -> None:
    remote = FakeRemote()
    app = create_app(remote, 'http://127.0.0.1:9999')
    raw = base64.b64encode(b'group,value\nA,1\nB,2\n').decode()

    with TestClient(app) as client:
        card = client.get('/.well-known/agent-card.json').json()
        assert card['supportedInterfaces'] == [
            {
                'url': 'http://127.0.0.1:9999',
                'protocolBinding': 'JSONRPC',
                'protocolVersion': '1.0',
            }
        ]
        assert card['capabilities']['streaming'] is True
        events = _stream(
            client,
            {
                'messageId': 'input-message',
                'contextId': 'scientific-context',
                'role': 'ROLE_USER',
                'parts': [
                    {'text': 'Compare the groups.', 'mediaType': 'text/plain'},
                    {
                        'raw': raw,
                        'filename': 'fixture.csv',
                        'mediaType': 'text/csv',
                    },
                ],
                'metadata': {
                    'enable_code': True,
                    'mcp_servers': ['context7', 'context7'],
                },
            },
        )

    states, artifacts = _states_and_artifacts(events)
    assert states == [
        'TASK_STATE_SUBMITTED',
        'TASK_STATE_WORKING',
        'TASK_STATE_COMPLETED',
    ]
    assert artifacts == {'report.md', 'run-summary.json'}
    assert len(remote.messages) == 1
    forwarded = remote.messages[0]
    assert forwarded.message_id != 'input-message'
    assert forwarded.context_id == 'scientific-context'
    assert not forwarded.task_id
    assert forwarded.parts[1].raw == base64.b64decode(raw)
    assert MessageToDict(forwarded.metadata) == {
        'enable_code': True,
        'mcp_servers': ['context7'],
    }


def test_remote_failure_never_becomes_local_completion() -> None:
    remote = FakeRemote(state=TaskState.TASK_STATE_FAILED, artifacts={})
    with TestClient(create_app(remote, 'http://127.0.0.1:9999')) as client:
        events = _stream(
            client,
            {
                'messageId': 'failure-message',
                'role': 'ROLE_USER',
                'parts': [{'text': 'Run a failing task.'}],
            },
        )

    states, artifacts = _states_and_artifacts(events)
    assert states == [
        'TASK_STATE_SUBMITTED',
        'TASK_STATE_WORKING',
        'TASK_STATE_FAILED',
    ]
    assert not artifacts


def test_message_sanitizer_rejects_urls_metadata_and_oversized_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url_message = Message(
        message_id='url-message',
        role=Role.ROLE_USER,
        parts=[Part(text='Read this.'), Part(url='https://example.com/file.csv')],
    )
    with pytest.raises(ValueError, match='Only text and raw file parts'):
        sanitize_message(url_message, 'context')

    metadata_message = Message(
        message_id='metadata-message',
        task_id='do-not-forward',
        role=Role.ROLE_USER,
        parts=[Part(text='Analyze this.')],
    )
    ParseDict({'unexpected': True}, metadata_message.metadata)
    with pytest.raises(ValueError, match='Unsupported message metadata'):
        sanitize_message(metadata_message, 'context')

    metadata_message.ClearField('metadata')
    forwarded = sanitize_message(metadata_message, 'context')
    assert not forwarded.task_id
    assert MessageToDict(forwarded.metadata) == {
        'enable_code': False,
        'mcp_servers': list(connector.DEFAULT_MCP_SERVERS),
    }

    monkeypatch.setattr(connector, 'MAX_RAW_FILE_BYTES', 3)
    file_message = Message(
        message_id='file-message',
        role=Role.ROLE_USER,
        parts=[
            Part(text='Analyze this.'),
            Part(raw=b'1234', filename='fixture.csv'),
        ],
    )
    with pytest.raises(ValueError, match='One raw file part exceeds'):
        sanitize_message(file_message, 'context')


def test_output_filter_requires_expected_types_and_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ConnectorError, match='not text'):
        bounded_output_parts(
            Artifact(
                artifact_id='bad-report',
                name='report.md',
                parts=[new_data_part({'not': 'text'})],
            )
        )
    monkeypatch.setattr(connector, 'MAX_REPORT_BYTES', 3)
    with pytest.raises(ConnectorError, match='exceeds the size limit'):
        bounded_output_parts(_artifact('report.md'))


def test_remote_card_must_keep_stable_jsonrpc_on_configured_origin() -> None:
    valid = AgentCard(
        name='Remote Evidence Bench',
        version='0.4.0',
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                protocol_version='1.0',
                url='https://bench.example.test/a2a',
            )
        ],
    )
    assert (
        connector._remote_jsonrpc_interface(valid, 'https://bench.example.test')
        == 'https://bench.example.test/a2a'
    )
    valid.supported_interfaces[0].url = 'https://attacker.example/a2a'
    with pytest.raises(ConnectorError, match='another origin'):
        connector._remote_jsonrpc_interface(valid, 'https://bench.example.test')


def test_remote_runner_uses_bearer_header_without_exposing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}
    card = AgentCard(
        name='Remote Evidence Bench',
        version='0.4.0',
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                protocol_version='1.0',
                url='https://bench.example.test/a2a',
            )
        ],
    )

    class FakeHttpClient:
        def __init__(self, **kwargs):
            captured['headers'] = kwargs['headers']

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakeResolver:
        def __init__(self, **kwargs):
            del kwargs

        async def get_agent_card(self):
            return card

    class FakeSdkClient:
        def send_message(self, request):
            captured['request'] = request

            async def responses():
                yield StreamResponse(
                    task=Task(
                        id='remote-task',
                        context_id='context',
                        status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                        artifacts=[
                            _artifact('report.md'),
                            _artifact('run-summary.json'),
                        ],
                    )
                )

            return responses()

        async def close(self):
            captured['closed'] = True

    async def fake_create_client(**kwargs):
        captured['client_config'] = kwargs['client_config']
        return FakeSdkClient()

    monkeypatch.setattr(connector.httpx, 'AsyncClient', FakeHttpClient)
    monkeypatch.setattr(connector, 'A2ACardResolver', FakeResolver)
    monkeypatch.setattr(connector, 'create_client', fake_create_client)
    runner = EvidenceBenchRemoteRunner(
        'https://bench.example.test',
        'highly-secret-token',
    )
    result = asyncio.run(
        runner.run(
            Message(
                message_id='safe-message',
                context_id='context',
                role=Role.ROLE_USER,
                parts=[Part(text='Analyze this.')],
            )
        )
    )

    assert result.state == TaskState.TASK_STATE_COMPLETED
    assert captured['headers']['Authorization'] == 'Bearer highly-secret-token'
    assert captured['headers']['A2A-Version'] == '1.0'
    assert captured['closed'] is True
    assert 'highly-secret-token' not in build_agent_card(
        'http://127.0.0.1:9999'
    ).SerializeToString().decode(errors='ignore')


def test_remote_runner_requires_token() -> None:
    with pytest.raises(ConnectorError, match='A2A_TOKEN is required'):
        EvidenceBenchRemoteRunner('https://bench.example.test', '')
