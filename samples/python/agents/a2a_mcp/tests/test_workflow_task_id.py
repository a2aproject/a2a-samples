# ruff: noqa
import ast
import importlib.util

from pathlib import Path
from types import SimpleNamespace


# Import the helper by file path. Importing a2a_mcp as a package runs
# a2a_mcp.__init__, which requires click and other runtime deps.
_SAMPLE_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = _SAMPLE_ROOT / 'src' / 'a2a_mcp' / 'common' / 'child_message.py'
_SPEC = importlib.util.spec_from_file_location('child_message', _HELPER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CHILD_MESSAGE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHILD_MESSAGE)
create_child_message_payload = _CHILD_MESSAGE.create_child_message_payload
child_task_id_from_result = _CHILD_MESSAGE.child_task_id_from_result

PARENT_TASK_ID = 'orchestrator-task-aaa'
CHILD_TASK_ID = 'child-task-bbb'
CONTEXT_ID = 'ctx-ccc'


_FUNC_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _parse_sample(relative_path: str) -> ast.Module:
    return ast.parse((_SAMPLE_ROOT / relative_path).read_text())


def _call_keywords(node: ast.AST, func_name: str) -> list[set[str]]:
    found: list[set[str]] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        called = child.func
        name = getattr(called, 'attr', getattr(called, 'id', None))
        if name == func_name:
            found.append({kw.arg for kw in child.keywords if kw.arg})
    return found


def test_first_child_message_omits_task_id() -> None:
    payload = create_child_message_payload(
        query='Plan a trip to Paris',
        context_id=CONTEXT_ID,
        task_id=None,
    )

    assert 'taskId' not in payload['message']
    assert payload['message']['contextId'] == CONTEXT_ID
    assert PARENT_TASK_ID not in payload['message'].values()


def test_resume_send_reuses_child_task_id() -> None:
    payload = create_child_message_payload(
        query='Use the same dates',
        context_id=CONTEXT_ID,
        task_id=CHILD_TASK_ID,
    )

    assert payload['message']['taskId'] == CHILD_TASK_ID
    assert payload['message']['taskId'] != PARENT_TASK_ID


def test_workflow_stores_child_task_id_and_reuses_it_on_resume() -> None:
    """First hop omits taskId; the child's returned id is reused on resume."""
    node_attrs: dict[str, str] = {
        'query': 'Plan a trip to Paris',
        'context_id': CONTEXT_ID,
    }

    first = create_child_message_payload(
        query=node_attrs['query'],
        context_id=node_attrs['context_id'],
        task_id=node_attrs.get('task_id'),
    )
    assert 'taskId' not in first['message']

    child_task = SimpleNamespace(id=CHILD_TASK_ID, status='submitted')
    status_event = SimpleNamespace(
        task_id=CHILD_TASK_ID,
        context_id=CONTEXT_ID,
    )
    stored_id = child_task_id_from_result(child_task)
    assert stored_id == child_task_id_from_result(status_event) == CHILD_TASK_ID
    assert stored_id != PARENT_TASK_ID
    node_attrs['task_id'] = stored_id

    resume = create_child_message_payload(
        query='Use the same dates',
        context_id=node_attrs['context_id'],
        task_id=node_attrs.get('task_id'),
    )
    assert resume['message']['taskId'] == CHILD_TASK_ID
    assert resume['message']['taskId'] != PARENT_TASK_ID


def test_orchestrator_does_not_stamp_parent_task_id_on_child_nodes() -> None:
    """Planner and follow-on nodes must not inherit the orchestrator task id."""
    tree = _parse_sample('src/a2a_mcp/agents/orchestrator_agent.py')
    add_graph_node = None
    stream = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'OrchestratorAgent':
            for item in node.body:
                if isinstance(item, _FUNC_TYPES):
                    if item.name == 'add_graph_node':
                        add_graph_node = item
                    elif item.name == 'stream':
                        stream = item
    assert add_graph_node is not None
    assert stream is not None

    add_params = [arg.arg for arg in add_graph_node.args.args]
    assert 'task_id' not in add_params

    for keywords in _call_keywords(add_graph_node, 'set_node_attributes'):
        assert 'task_id' not in keywords
    for keywords in _call_keywords(stream, 'add_graph_node'):
        assert 'task_id' not in keywords
    for keywords in _call_keywords(stream, 'set_node_attributes'):
        assert 'task_id' not in keywords


def test_run_node_omits_task_id_unless_child_already_owns_it() -> None:
    workflow_path = _SAMPLE_ROOT / 'src/a2a_mcp/common/workflow.py'
    source = workflow_path.read_text()
    assert "'taskId': task_id" not in source

    tree = ast.parse(source)
    run_node = None
    run_workflow = None
    for node in ast.walk(tree):
        if isinstance(node, _FUNC_TYPES) and node.name == 'run_node':
            run_node = node
        if isinstance(node, _FUNC_TYPES) and node.name == 'run_workflow':
            run_workflow = node
    assert run_node is not None
    assert run_workflow is not None
    assert _call_keywords(run_node, 'create_child_message_payload')
    assert _call_keywords(run_workflow, 'child_task_id_from_result')
