# ruff: noqa: S101, PLR2004, TC002 - plain asserts and literals read best in tests
"""Tests for the Jev router and the executor that forwards to the chosen agent.

Run from this directory: ``uv run pytest test_jev_router.py``. Jev is mocked with an
``httpx.MockTransport``; the remote agents run in-process over ASGI. One live test runs only
when ``TYPESAFE_API_KEY`` is set.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from typing import Any

import httpx
import pytest

from a2a.client import A2AClient
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    DataPart,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TaskState,
    TextPart,
)
from a2a.utils import get_message_text, new_task
from jev_host_executor import NO_AGENT_TEXT, JevRoutingExecutor
from jev_router import NONE_KEY, JevRouter, candidates_from_cards
from remote_agent_connection import RemoteAgentConnections


def run(coro: Any) -> Any:
    """Run a coroutine to completion (no pytest-asyncio dependency)."""
    return asyncio.run(coro)


def make_card(name: str, description: str, skills: list[AgentSkill], url: str) -> AgentCard:
    """A card shaped like the sample agents'."""
    return AgentCard(
        name=name,
        description=description,
        url=url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
    )


WEATHER = make_card(
    'Weather Agent',
    'Helps with weather',
    [
        AgentSkill(
            id='weather_search',
            name='Search weather',
            description='Helps with weather in city, or states',
            tags=['weather'],
            examples=['weather in LA, CA'],
        )
    ],
    'http://weather.test',
)
AIRBNB = make_card(
    'Airbnb Agent',
    'Helps with searching accommodation',
    [
        AgentSkill(
            id='airbnb_search',
            name='Search airbnb accommodation',
            description='Helps with accommodation search using airbnb',
            tags=['airbnb accommodation'],
            examples=['Find a room in LA, CA, April 15-18, 2025, two adults'],
        )
    ],
    'http://airbnb.test',
)
CARDS = [WEATHER, AIRBNB]
WEATHER_KEY = 'weather-agent__weather-search'
AIRBNB_KEY = 'airbnb-agent__airbnb-search'


class FakeJev:
    """An ``httpx.MockTransport`` handler that picks the option whose text mentions a word."""

    def __init__(self, word: str, status: int = 200) -> None:
        self.word = word
        self.status = status
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        if self.status != 200:
            return httpx.Response(self.status, json={'error': 'nope'})
        criteria: dict[str, str] = body['questions']['route']['criteria']
        chosen = next(
            (k for k, text in criteria.items() if k != NONE_KEY and self.word in text.lower()),
            NONE_KEY,
        )
        others = [k for k in criteria if k != chosen]
        probabilities = {k: (0.9 if k == chosen else 0.1 / len(others)) for k in criteria}
        return httpx.Response(
            200,
            json={
                'model': 'jev-1.13.0',
                'answers': {
                    'route': {
                        'type': 'choice',
                        'choice': chosen,
                        'confidence': 0.88,
                        'probabilities': probabilities,
                    }
                },
                'usage': {'input_tokens': 400 + len(criteria), 'output_tokens': 40},
            },
        )


def router_with(fake: FakeJev) -> JevRouter:
    """A router whose HTTP goes to the fake."""
    return JevRouter(api_key='test', client=httpx.AsyncClient(transport=httpx.MockTransport(fake)))


# --- router -----------------------------------------------------------------------


def test_candidates_from_cards() -> None:
    candidates = candidates_from_cards(CARDS)
    assert [c.key for c in candidates] == [WEATHER_KEY, AIRBNB_KEY]
    assert candidates[0].agent_name == 'Weather Agent'
    assert candidates[0].skill_id == 'weather_search'
    assert 'Tags: weather' in candidates[0].description
    assert 'Examples: weather in LA, CA' in candidates[0].description
    bare = make_card('Bare Agent', 'Answers trivia', [], 'http://bare.test')
    assert candidates_from_cards([bare])[0].key == 'bare-agent__agent'


def test_route_maps_the_answer() -> None:
    fake = FakeJev('weather')
    route = run(router_with(fake).route('weather in LA, CA', CARDS))
    assert route.agent_name == 'Weather Agent'
    assert route.skill_id == 'weather_search'
    assert route.confidence == 0.88
    assert set(route.probabilities) == {WEATHER_KEY, AIRBNB_KEY, NONE_KEY}
    assert route.model == 'jev-1.13.0'
    assert route.usage == {'input_tokens': 403, 'output_tokens': 40}
    assert route.latency_ms >= 0
    body = fake.requests[0]
    assert body['state'] == {'request': 'weather in LA, CA'}
    assert body['questions']['route']['criteria'][NONE_KEY]
    assert body['model'] == 'jev-latest'
    assert route.as_dict()['agent_name'] == 'Weather Agent'


def test_route_none_means_no_agent() -> None:
    route = run(router_with(FakeJev('poetry')).route('write me a limerick', CARDS))
    assert route.agent_name is None
    assert route.skill_id is None
    assert route.probabilities[NONE_KEY] == 0.9


def test_route_propagates_http_errors() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        run(router_with(FakeJev('weather', status=500)).route('weather', CARDS))


def test_route_refuses_rosters_that_do_not_fit_one_question() -> None:
    cards = [
        make_card(
            f'Agent {i}',
            f'agent {i}',
            [AgentSkill(id=f's{i}', name=f'S{i}', description='d', tags=[])],
            'http://x',
        )
        for i in range(255)
    ]
    with pytest.raises(ValueError, match='do not fit'):
        run(router_with(FakeJev('x')).route('hi', cards))
    with pytest.raises(ValueError, match='no remote agents'):
        run(router_with(FakeJev('x')).route('hi', []))


# --- executor, over in-process A2A ---------------------------------------------------


class EchoExecutor(AgentExecutor):
    """Completes every task with one text artifact naming the agent."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Answer immediately."""
        task = context.current_task or new_task(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        text = f'{self.name} handled: {get_message_text(context.message)}'
        await updater.add_artifact([Part(root=TextPart(text=text))])
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported."""
        raise NotImplementedError


class AskThenAnswerExecutor(EchoExecutor):
    """Asks for dates on the first message of a context, answers on the second."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.seen: set[str] = set()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """First turn: input required. Second turn: complete."""
        task = context.current_task or new_task(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        if task.context_id not in self.seen:
            self.seen.add(task.context_id)
            await updater.requires_input(
                updater.new_agent_message([Part(root=TextPart(text='Which dates?'))])
            )
            return
        await updater.add_artifact(
            [Part(root=TextPart(text=f'{self.name} booked: {get_message_text(context.message)}'))]
        )
        await updater.complete()


def serve(card: AgentCard, executor: AgentExecutor) -> httpx.AsyncClient:
    """Serve ``card`` from an in-process ASGI app and return a client bound to it."""
    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())
    app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=card.url)


def connection(card: AgentCard, client: httpx.AsyncClient) -> RemoteAgentConnections:
    """A remote connection whose HTTP goes to the in-process app."""
    conn = RemoteAgentConnections(agent_card=card, agent_url=card.url)
    conn.agent_client = A2AClient(client, card)
    return conn


HOST = make_card('Host', 'routes with jev', [], 'http://host.test')


def host_client(executor: JevRoutingExecutor) -> httpx.AsyncClient:
    """Serve the host executor itself in-process."""
    return serve(HOST, executor)


async def send(
    client: httpx.AsyncClient, text: str, task_id: str | None = None, context_id: str | None = None
) -> Task:
    """Send one text message to the host and return the resulting task."""
    message: dict[str, Any] = {
        'role': 'user',
        'parts': [{'kind': 'text', 'text': text}],
        'messageId': uuid.uuid4().hex,
    }
    if task_id:
        message['taskId'] = task_id
    if context_id:
        message['contextId'] = context_id
    request = SendMessageRequest(
        id=uuid.uuid4().hex, params=MessageSendParams.model_validate({'message': message})
    )
    response = await A2AClient(client, HOST).send_message(request)
    assert isinstance(response.root, SendMessageSuccessResponse), response.root
    assert isinstance(response.root.result, Task)
    return response.root.result


def artifact_texts(task: Task) -> list[str]:
    """Text of every text part on the task's artifacts."""
    return [
        p.root.text for a in (task.artifacts or []) for p in a.parts if isinstance(p.root, TextPart)
    ]


def routing_artifact(task: Task) -> dict[str, Any]:
    """The route Jev returned, as relayed on the host task."""
    for a in task.artifacts or []:
        if a.name == 'routing':
            (part,) = a.parts
            assert isinstance(part.root, DataPart)
            return part.root.data['route']
    raise AssertionError('no routing artifact')


def test_executor_routes_and_relays() -> None:
    async def scenario() -> None:
        weather = serve(WEATHER, EchoExecutor('Weather Agent'))
        airbnb = serve(AIRBNB, EchoExecutor('Airbnb Agent'))
        fake = FakeJev('accommodation')
        executor = JevRoutingExecutor(
            router_with(fake),
            CARDS,
            connections={
                'Weather Agent': connection(WEATHER, weather),
                'Airbnb Agent': connection(AIRBNB, airbnb),
            },
        )
        async with host_client(executor) as host:
            task = await send(host, 'find a room in Lisbon')
            assert task.status.state == TaskState.completed
            assert artifact_texts(task) == ['Airbnb Agent handled: find a room in Lisbon']
            route = routing_artifact(task)
            assert route['agent_name'] == 'Airbnb Agent'
            assert route['confidence'] == 0.88
            assert route['usage']['input_tokens'] > 0
        await weather.aclose()
        await airbnb.aclose()

    run(scenario())


def test_executor_completes_with_a_note_when_nothing_fits() -> None:
    async def scenario() -> None:
        fake = FakeJev('poetry')
        executor = JevRoutingExecutor(router_with(fake), CARDS, connections={})
        async with host_client(executor) as host:
            task = await send(host, 'write me a limerick')
            assert task.status.state == TaskState.completed
            assert get_message_text(task.status.message) == NO_AGENT_TEXT
            assert routing_artifact(task)['agent_name'] is None

    run(scenario())


def test_executor_fails_the_task_when_jev_is_down() -> None:
    async def scenario() -> None:
        executor = JevRoutingExecutor(router_with(FakeJev('x', status=500)), CARDS, connections={})
        async with host_client(executor) as host:
            task = await send(host, 'weather in LA')
            assert task.status.state == TaskState.failed
            assert 'Routing failed' in get_message_text(task.status.message)

    run(scenario())


def test_follow_up_goes_back_to_the_agent_that_asked() -> None:
    async def scenario() -> None:
        airbnb = serve(AIRBNB, AskThenAnswerExecutor('Airbnb Agent'))
        fake = FakeJev('accommodation')
        executor = JevRoutingExecutor(
            router_with(fake), CARDS, connections={'Airbnb Agent': connection(AIRBNB, airbnb)}
        )
        async with host_client(executor) as host:
            first = await send(host, 'book a place in Rome')
            assert first.status.state == TaskState.input_required
            assert get_message_text(first.status.message) == 'Which dates?'
            second = await send(host, '3 to 5 May', task_id=first.id, context_id=first.context_id)
            assert second.status.state == TaskState.completed
            assert artifact_texts(second)[-1] == 'Airbnb Agent booked: 3 to 5 May'
        # Jev was consulted once; the follow-up reused the waiting agent.
        assert len(fake.requests) == 1
        await airbnb.aclose()

    run(scenario())


# --- live ------------------------------------------------------------------------------


@pytest.mark.skipif(not os.getenv('TYPESAFE_API_KEY'), reason='TYPESAFE_API_KEY not set')
def test_live_jev_routes_weather() -> None:
    router = JevRouter(api_key=os.environ['TYPESAFE_API_KEY'])
    route = run(router.route('What is the weather like in LA, CA this weekend?', CARDS))
    assert route.agent_name == 'Weather Agent'
    assert route.confidence > 0.5
    assert route.usage['input_tokens'] > 0
    poem = run(router.route('Write me a limerick about a cat', CARDS))
    assert poem.agent_name is None
