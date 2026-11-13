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
