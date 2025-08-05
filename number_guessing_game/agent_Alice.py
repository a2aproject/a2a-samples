"""agent_Alice.py
AgentAlice – the evaluator in the toy A2A number-guessing demo.

This agent picks a secret integer between 1 and 100 when the process
starts and evaluates incoming guesses sent via the A2A `message/send`
operation.  For each guess it responds with one of the following hints:

* ``"Go higher"`` – the guess was lower than the secret.
* ``"Go lower"``  – the guess was higher than the secret.
* ``"correct! attempts: <n>"`` – the guess was correct; ``n`` is the
  number of attempts taken so far.

The module exposes a single public callable, :pyfunc:`alice_handler`,
which is executed via the A2A SDK server stack using
:pyfunc:`utils.server.run_agent_blocking` and runs inside an HTTP
server started in the ``__main__`` block.

The agent is implemented with the official A2A Python SDK and a small helper
layer – the code focuses on game logic rather than protocol plumbing.
"""

import uuid

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentCard, Part, TextPart
from a2a.utils.message import get_message_text
from config import AGENT_ALICE_PORT
from utils.game_logic import process_guess
from utils.server import run_agent_blocking


# ------------------ Agent card ------------------

alice_skills = [
    {
        'id': 'number_guess_evaluator',
        'name': 'Number Guess Evaluator',
        'description': 'Evaluates numeric guesses (1-100) against a secret number and replies with guidance (higher/lower/correct).',
        'tags': ['game', 'demo'],
        'inputModes': ['text/plain'],
        'outputModes': ['text/plain'],
        'examples': ['50'],
    }
]

alice_card_dict = {
    'name': 'AgentAlice',
    'description': 'Hosts the number-guessing game by picking a secret number and grading guesses.',
    'url': f'http://localhost:{AGENT_ALICE_PORT}/a2a/v1',
    'preferredTransport': 'JSONRPC',
    'protocolVersion': '0.3.0',
    'version': '1.0.0',
    'capabilities': {
        'streaming': False,
        'pushNotifications': False,
        'stateTransitionHistory': False,
    },
    'defaultInputModes': ['text/plain'],
    'defaultOutputModes': ['text/plain'],
    'skills': alice_skills,
}
alice_card = AgentCard.model_validate(alice_card_dict)

# ------------------ Internal helpers ------------------


class NumberGuessExecutor(AgentExecutor):
    """AgentExecutor implementing the number‐guessing logic directly."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Handle a newly received message from a peer agent."""
        raw_text = get_message_text(context.message) if context.message else ''
        response_text = process_guess(raw_text)

        updater = TaskUpdater(
            event_queue,
            task_id=context.task_id or str(uuid.uuid4()),
            context_id=context.context_id or str(uuid.uuid4()),
        )
        # Tell the client that the task has started, then publish the answer and
        # finally mark it completed so Bob sees a full Task object with the
        # artifact attached.
        await updater.submit()
        await updater.add_artifact([Part(root=TextPart(text=response_text))])
        await updater.complete()

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Reject the referenced task if one is supplied."""
        if context.task_id:
            updater = TaskUpdater(
                event_queue,
                task_id=context.task_id,
                context_id=context.context_id or str(uuid.uuid4()),
            )
            await updater.reject()


if __name__ == '__main__':
    run_agent_blocking(
        name='AgentAlice',
        port=AGENT_ALICE_PORT,
        agent_card=alice_card,
        executor=NumberGuessExecutor(),
    )
