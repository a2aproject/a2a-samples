"""a2a_server.py -- Multi-tenancy demo: three A2A agents behind ONE host.

Companion to the "A2A Multi-Tenancy" blog post. Run it, then run a2a_client.py.

    pip install "a2a-sdk>=1.0.3" uvicorn starlette httpx
    python a2a_server.py

It hosts three tiny "echo-style" agents, each on its own URL sub-path:

    http://127.0.0.1:9999/hello       -> Hello World agent  (says hello)
    http://127.0.0.1:9999/palindrome  -> Palindrome agent   (is it a palindrome?)
    http://127.0.0.1:9999/reverse     -> Word-reverse agent (reverses word order)

Each agent publishes its own Agent Card at <sub-path>/.well-known/agent-card.json,
so a client just reads the card and sends requests where it points.
"""

import os

from collections.abc import Callable

import uvicorn

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import TaskState
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from starlette.applications import Starlette


BIND_HOST = os.environ.get('A2A_BIND_HOST', '127.0.0.1')
PORT = int(os.environ.get('A2A_PORT', '9999'))
PUBLIC_URL = os.environ.get('A2A_PUBLIC_URL', f'http://127.0.0.1:{PORT}')


# --- The three agent "brains": trivial text -> text functions. ---


def hello_world(text: str) -> str:
    """Classic hello-world echo."""
    return f'Hello, World! You said: "{text}"'


def palindrome(text: str) -> str:
    """Report whether the input reads the same forwards and backwards."""
    cleaned = ''.join(ch.lower() for ch in text if ch.isalnum())
    if not cleaned:
        return 'Send me some text and I will check if it is a palindrome.'
    verdict = 'is' if cleaned == cleaned[::-1] else 'is not'
    return f'"{text}" {verdict} a palindrome.'


def reverse_words(text: str) -> str:
    """Reverse the order of the words in the input."""
    if not text.strip():
        return 'Send me a sentence and I will reverse the word order.'
    return f'Reversed: {" ".join(reversed(text.split()))}'


# --- One small AgentExecutor, parameterized by a transform function. ---


class SimpleAgentExecutor(AgentExecutor):
    """Runs one text -> text transform; A2A does the rest of the work."""

    def __init__(self, transform: Callable[[str], str]) -> None:
        self.transform = transform

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process user request."""
        # 1. Collect a task from the request context.
        if context.current_task:
            task = context.current_task
        else:
            # 1.1 If there is no task, create one and add it to the event queue.
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        # 2. Update task status in the EventQueue using a TaskUpdater object.
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message('Working on it...'),
        )

        # 3. Collect the user's text and run this tenant's transform on it.
        query = get_message_text(context.message)
        result = self.transform(query) if query else 'No text input was provided!'

        # 4. Add the generated response as an artifact to the EventQueue.
        await updater.add_artifact(parts=[new_text_part(text=result, media_type='text/plain')])

        # 5. Mark the task completed.
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message('Done!'),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Raise exception as cancel is not supported."""
        raise NotImplementedError('Cancel is not supported.')


def build_card(  # noqa: PLR0913 - demo helper: one clear arg per card field
    path: str,
    name: str,
    description: str,
    skill_id: str,
    skill_name: str,
    examples: list[str],
) -> AgentCard:
    """Each agent advertises its OWN card, pointing at its OWN sub-path."""
    return AgentCard(
        # Basic identity information for this tenant's A2A server.
        name=name,
        description=description,
        version='1.0.0',
        # Default media types for the agent's interactions.
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        # Supported A2A features (here, streaming responses).
        capabilities=AgentCapabilities(streaming=True),
        # The endpoint(s) where this agent can be reached. This is the heart of
        # sub-path routing: each card points clients at its own URL prefix.
        supported_interfaces=[
            AgentInterface(
                protocol_binding='JSONRPC',
                url=f'{PUBLIC_URL}{path}',
                protocol_version='1.0',
            )
        ],
        # The list of AgentSkill objects this agent offers.
        skills=[
            AgentSkill(
                id=skill_id,
                name=skill_name,
                description=description,
                input_modes=['text/plain'],
                output_modes=['text/plain'],
                tags=['a2a', 'echo-example', 'multi-tenancy'],
                examples=examples,
            )
        ],
    )


# One (sub-path, card, executor) entry per tenant agent.
AGENTS = [
    (
        '/hello',
        build_card(
            '/hello',
            'Hello World Agent',
            'Replies with a friendly hello.',
            'hello',
            'Say hello',
            ['hi', 'hello there'],
        ),
        SimpleAgentExecutor(hello_world),
    ),
    (
        '/palindrome',
        build_card(
            '/palindrome',
            'Palindrome Agent',
            'Tells you whether your text is a palindrome.',
            'palindrome',
            'Palindrome check',
            ['racecar', 'hello'],
        ),
        SimpleAgentExecutor(palindrome),
    ),
    (
        '/reverse',
        build_card(
            '/reverse',
            'Word Reverse Agent',
            'Reverses the order of the words in your text.',
            'reverse',
            'Reverse words',
            ['hello world', 'agents talking to agents'],
        ),
        SimpleAgentExecutor(reverse_words),
    ),
]


def build_app() -> Starlette:
    """Mount each agent's card + JSON-RPC endpoint on its own sub-path."""
    routes = []
    for path, card, executor in AGENTS:
        # The RequestHandler processes incoming requests and manages tasks for
        # this one tenant, backed by its own in-memory task store.
        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
            agent_card=card,
        )
        # Publish this agent's Agent Card under <sub-path>/.well-known/... so
        # clients can discover it independently of the other tenants.
        routes.extend(
            create_agent_card_routes(card, card_url=f'{path}{AGENT_CARD_WELL_KNOWN_PATH}')
        )
        # Mount this agent's JSON-RPC endpoint on its own sub-path.
        routes.extend(create_jsonrpc_routes(handler, rpc_url=path))
    # A single Starlette app fronts all three agents on one host/port.
    return Starlette(routes=routes)


if __name__ == '__main__':
    print(f'Serving three A2A agents (bind {BIND_HOST}:{PORT}, public {PUBLIC_URL}):')
    for sub_path, agent_card, _ in AGENTS:
        print(f'  {PUBLIC_URL}{sub_path}  ->  {agent_card.name}')
    uvicorn.run(build_app(), host=BIND_HOST, port=PORT)
