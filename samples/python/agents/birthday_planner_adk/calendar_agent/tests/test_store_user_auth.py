import asyncio
import importlib.util
import sys

from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch


_AGENT_DIR = Path(__file__).resolve().parents[1]
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))


class _StubAgentExecutor:
    """Stand-in for a2a.server.agent_execution.AgentExecutor."""


def _ensure_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module
    module = ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    parent_name, _, attr = name.rpartition('.')
    if parent_name:
        setattr(_ensure_module(parent_name), attr, module)
    return module


def _missing(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is None
    except ModuleNotFoundError:
        return True


def _set_attr(module: ModuleType, name: str, value: object) -> None:
    if not hasattr(module, name):
        setattr(module, name, value)


def _install_import_stubs() -> None:
    """Let this test import the executor without the sample's runtime extras."""
    agent_execution = _ensure_module('a2a.server.agent_execution')
    _set_attr(agent_execution, 'AgentExecutor', _StubAgentExecutor)
    _set_attr(agent_execution, 'RequestContext', MagicMock)
    _set_attr(
        _ensure_module('a2a.server.agent_execution.context'),
        'RequestContext',
        agent_execution.RequestContext,
    )
    _set_attr(_ensure_module('a2a.server.events.event_queue'), 'EventQueue', MagicMock)
    _set_attr(_ensure_module('a2a.server.tasks'), 'TaskUpdater', MagicMock)
    a2a_types = _ensure_module('a2a.types')
    for type_name in (
        'AgentCard',
        'FilePart',
        'FileWithBytes',
        'FileWithUri',
        'Part',
        'TextPart',
        'UnsupportedOperationError',
    ):
        _set_attr(a2a_types, type_name, MagicMock)

    class _TaskState:
        working = 'working'
        failed = 'failed'
        auth_required = 'auth_required'

    a2a_types.TaskState = _TaskState
    _set_attr(_ensure_module('a2a.utils.errors'), 'ServerError', Exception)
    _set_attr(
        _ensure_module('a2a.utils.message'),
        'new_agent_text_message',
        MagicMock(),
    )
    if _missing('google.adk'):
        _ensure_module('google.adk').Runner = MagicMock
        adk_auth = _ensure_module('google.adk.auth')
        for type_name in ('AuthConfig', 'AuthCredential', 'AuthScheme'):
            setattr(adk_auth, type_name, MagicMock)
        adk_events = _ensure_module('google.adk.events')
        for type_name in ('Event', 'EventActions'):
            setattr(adk_events, type_name, MagicMock)
        _ensure_module('google.adk.sessions').Session = MagicMock
        _ensure_module(
            'google.adk.tools.openapi_tool.openapi_spec_parser.tool_auth_handler'
        ).ToolContextCredentialStore = MagicMock
    if _missing('google.genai'):
        _ensure_module('google.genai').types = MagicMock()


_install_import_stubs()

from adk_agent_executor import ADKAgentExecutor, ADKAuthDetails


def test_complete_auth_processing_stores_credential_when_unauthenticated() -> None:
    """OAuth callback without a JWT must still cache the session credential."""
    asyncio.run(_run_complete_auth_processing_unauthenticated())


async def _run_complete_auth_processing_unauthenticated() -> None:
    runner = MagicMock()
    runner.app_name = 'Calendar Agent'
    executor = ADKAgentExecutor(runner, MagicMock())

    credential = object()
    session = MagicMock()
    session.user_id = 'anonymous'
    session.state = {'calendar-oauth-key': credential}

    user = MagicMock()
    user.is_authenticated = False
    user.user_name = 'jwt-user'
    call_context = MagicMock()
    call_context.user = user
    context = MagicMock()
    context.call_context = call_context
    context.context_id = 'ctx-unauthenticated'

    future = asyncio.get_running_loop().create_future()
    future.set_result('http://localhost:10007/authenticate?code=abc&state=xyz')

    auth_config = MagicMock()
    auth_config.exchanged_auth_credential.oauth2 = MagicMock()
    auth_config.auth_scheme = MagicMock()
    auth_config.raw_auth_credential = MagicMock()
    auth_details = ADKAuthDetails(
        state='xyz',
        uri='https://accounts.google.com/o/oauth2/auth',
        future=future,
        auth_config=auth_config,
        auth_request_function_call_id='fn-1',
    )
    executor._awaiting_auth[auth_details.state] = future  # noqa: SLF001

    task_updater = MagicMock()
    task_updater.update_status = AsyncMock()

    with (
        patch.object(executor, '_process_request', new_callable=AsyncMock),
        patch.object(executor, '_upsert_session', new_callable=AsyncMock, return_value=session),
        patch('adk_agent_executor.ToolContextCredentialStore') as store_cls,
    ):
        store_cls.return_value.get_credential_key.return_value = 'calendar-oauth-key'
        await executor._complete_auth_processing(  # noqa: SLF001
            context, auth_details, task_updater
        )

    assert session.user_id in executor._credentials  # noqa: S101, SLF001
    stored = executor._credentials[session.user_id]  # noqa: SLF001
    assert stored.key == 'calendar-oauth-key'  # noqa: S101
    assert stored.credential is credential  # noqa: S101
    assert user.user_name not in executor._credentials  # noqa: S101, SLF001
