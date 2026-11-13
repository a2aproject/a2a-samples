# ruff: noqa: S101
import asyncio
import sys

from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from no_llm_framework.server.agent import (
    Agent,
    build_called_tool_record,
    called_tools_history_template,
)


DECIDE_TURNS = 2


def test_history_template_renders_name_from_builder() -> None:
    tool = {
        'name': 'fetch_A2A_documentation',
        'arguments': {'query': 'A2A'},
    }
    result = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text='protocol overview')],
    )

    record = build_called_tool_record(tool, result)
    rendered = called_tools_history_template.render(called_tools=[record])

    assert record['name'] == 'fetch_A2A_documentation'
    assert 'tool' not in record
    assert '- Tool: fetch_A2A_documentation' in rendered
    assert '- isError: False' in rendered
    assert 'protocol overview' in rendered


def test_stream_complete_event_uses_model_answer() -> None:
    tool_call = '```json\n[{"name": "fetch_A2A_documentation", "arguments": {"query": "A2A"}}]\n```'
    model_answer = '<Answer>\nA2A is an agent-to-agent protocol.\n</Answer>'
    decide_history: list[list[dict]] = []

    async def fake_decide(question: str, called_tools: list[dict] | None = None) -> object:
        del question
        decide_history.append(list(called_tools or []))
        if not called_tools:
            return iter([tool_call])
        return iter([model_answer])

    async def fake_call_tool(tools: list[dict]) -> list[SimpleNamespace]:
        del tools
        return [
            SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(text='docs')],
            )
        ]

    async def collect_events() -> list[dict]:
        agent = Agent(mcp_url='https://example.test/mcp')
        agent.decide = fake_decide
        agent.call_tool = fake_call_tool
        return [event async for event in agent.stream('What is A2A?')]

    events = asyncio.run(collect_events())
    complete_events = [event for event in events if event['is_task_complete']]
    contents = [event['content'] for event in events]

    assert len(complete_events) == 1
    assert complete_events[0]['content'] == model_answer
    assert complete_events[0]['content'] != 'Task completed'
    assert not any(content.startswith('Step ') for content in contents)
    assert 'Previous tools have been called.' not in contents
    assert len(decide_history) == DECIDE_TURNS
    assert decide_history[1][0]['name'] == 'fetch_A2A_documentation'
