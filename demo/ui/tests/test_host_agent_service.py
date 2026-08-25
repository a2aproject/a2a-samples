# ruff: noqa
import ast
import types
import unittest

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


_UI_ROOT = Path(__file__).resolve().parents[1]
_HOST_AGENT_SERVICE = _UI_ROOT / 'state' / 'host_agent_service.py'
_IN_MEMORY_MANAGER = _UI_ROOT / 'service' / 'server' / 'in_memory_manager.py'


def _strip_annotations(node: ast.AST) -> None:
    """Drop annotations so extracted defs do not need imported types."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return
    node.returns = None
    for arg in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        arg.annotation = None
    if node.args.vararg is not None:
        node.args.vararg.annotation = None
    if node.args.kwarg is not None:
        node.args.kwarg.annotation = None


def _load_defs(path: Path, names: set[str]) -> dict[str, object]:
    """Load selected function bodies from a source file without importing it."""
    tree = ast.parse(path.read_text(), filename=str(path))
    nodes: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            _strip_annotations(node)
            nodes.append(node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in names:
                    _strip_annotations(item)
                    nodes.append(item)
    missing = names - {getattr(node, 'name', '') for node in nodes}
    if missing:
        raise AssertionError(f'Could not find {sorted(missing)} in {path}')
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), 'exec'), namespace)  # noqa: S102
    return namespace


class _Request:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs


_HELPERS = _load_defs(
    _HOST_AGENT_SERVICE,
    {'ListRemoteAgents', 'GetProcessingMessages', 'GetTasks'},
)
_HELPERS['ListAgentRequest'] = _Request
_HELPERS['PendingMessageRequest'] = _Request
_HELPERS['ListTaskRequest'] = _Request
_HELPERS['server_url'] = 'http://localhost:12000'

_MANAGER_METHODS = _load_defs(_IN_MEMORY_MANAGER, {'get_pending_messages', 'events'})

ListRemoteAgents = _HELPERS['ListRemoteAgents']
GetProcessingMessages = _HELPERS['GetProcessingMessages']
GetTasks = _HELPERS['GetTasks']


class _FakeManager:
    """Minimal stand-in that exercises InMemoryFakeAgentManager methods."""

    def __init__(self) -> None:
        self._pending_message_ids: list[str] = []
        self._task_map: dict[str, str] = {}
        self._tasks: list[object] = []
        self._events: list[object] = []

    get_pending_messages = _MANAGER_METHODS['get_pending_messages']
    # events is already a property: _load_defs execs the @property-decorated method.
    events = _MANAGER_METHODS['events']


class HostAgentServiceTest(unittest.IsolatedAsyncioTestCase):
    """Regression tests for conversation-server client helpers."""

    async def test_list_remote_agents_returns_empty_list_on_error(self) -> None:
        client = MagicMock()
        client.list_agents = AsyncMock(side_effect=Exception('All connection attempts failed'))
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await ListRemoteAgents()
        self.assertEqual(result, [])

    async def test_list_remote_agents_returns_empty_list_when_result_missing(
        self,
    ) -> None:
        client = MagicMock()
        client.list_agents = AsyncMock(return_value=MagicMock(result=None))
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await ListRemoteAgents()
        self.assertEqual(result, [])

    async def test_get_processing_messages_returns_empty_dict_on_error(
        self,
    ) -> None:
        client = MagicMock()
        client.get_pending_messages = AsyncMock(
            side_effect=Exception('All connection attempts failed')
        )
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await GetProcessingMessages()
        self.assertEqual(result, {})

    async def test_get_processing_messages_returns_empty_dict_when_result_missing(
        self,
    ) -> None:
        client = MagicMock()
        client.get_pending_messages = AsyncMock(return_value=MagicMock(result=None))
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await GetProcessingMessages()
        self.assertEqual(result, {})

    async def test_get_tasks_returns_empty_list_on_error(self) -> None:
        client = MagicMock()
        client.list_tasks = AsyncMock(side_effect=Exception('All connection attempts failed'))
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await GetTasks()
        self.assertEqual(result, [])

    async def test_get_tasks_returns_empty_list_when_result_missing(self) -> None:
        client = MagicMock()
        client.list_tasks = AsyncMock(return_value=MagicMock(result=None))
        with patch.dict(_HELPERS, {'ConversationClient': MagicMock(return_value=client)}):
            result = await GetTasks()
        self.assertEqual(result, [])


class InMemoryFakeAgentManagerTest(unittest.TestCase):
    """Regression tests for fake-host pending messages and events."""

    def test_get_pending_messages_returns_all_ids(self) -> None:
        manager = _FakeManager()
        manager._pending_message_ids.extend(['msg-1', 'msg-2'])
        self.assertEqual(
            manager.get_pending_messages(),
            [('msg-1', ''), ('msg-2', '')],
        )

    def test_get_pending_messages_fallback_when_task_has_no_history_parts(
        self,
    ) -> None:
        manager = _FakeManager()
        manager._pending_message_ids.append('msg-1')
        manager._task_map['msg-1'] = 'task-1'
        manager._tasks.append(types.SimpleNamespace(id='task-1', history=[]))
        self.assertEqual(manager.get_pending_messages(), [('msg-1', '')])

    def test_get_pending_messages_reports_status_for_each_id(self) -> None:
        manager = _FakeManager()
        manager._pending_message_ids.extend(['msg-1', 'msg-2'])
        manager._task_map['msg-1'] = 'task-1'
        message = types.SimpleNamespace(
            parts=[types.SimpleNamespace(root=types.SimpleNamespace(kind='text', text='hi'))]
        )
        manager._tasks.append(types.SimpleNamespace(id='task-1', history=[message]))
        self.assertEqual(
            manager.get_pending_messages(),
            [('msg-1', 'Working...'), ('msg-2', '')],
        )

    def test_events_returns_stored_list(self) -> None:
        manager = _FakeManager()
        manager._events.append(types.SimpleNamespace(id='evt-1'))
        self.assertEqual(len(manager.events), 1)
        self.assertEqual(manager.events[0].id, 'evt-1')


class AgentListPageTest(unittest.TestCase):
    """The Agents page must not pass None into the Mesop list component."""

    def test_page_coerces_none_agents_to_empty_list(self) -> None:
        source = (_UI_ROOT / 'pages' / 'agent_list.py').read_text()
        self.assertIn('agents_list(agents or [])', source)


if __name__ == '__main__':
    unittest.main()
