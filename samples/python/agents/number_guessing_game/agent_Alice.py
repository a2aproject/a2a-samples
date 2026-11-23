#!/usr/bin/env python3
"""AgentAlice - the evaluator in the toy A2A number-guessing demo.

This agent picks a secret integer between 1 and 100 when the process
starts and evaluates incoming guesses sent via the A2A `SendMessage`
operation.  For each guess it responds with one of the following hints:

* ``"Go higher"`` - the guess was lower than the secret.
* ``"Go lower"``  - the guess was higher than the secret.
* ``"correct! attempts: <n>"`` - the guess was correct; ``n`` is the
  number of attempts taken so far.

The module exposes a single public callable, :pyfunc:`alice_handler`,
which is executed via the A2A SDK server stack using
:pyfunc:`utils.server.run_agent_blocking` and runs inside an HTTP
server started in the ``__main__`` block.

The agent is implemented with the official A2A Python SDK and a small helper
layer - the code focuses on game logic rather than protocol plumbing.
"""

import uuid

from a2a.helpers import get_message_text, new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
)
from config import AGENT_ALICE_PORT
from utils.game_logic import process_guess
from utils.server import run_agent_blocking


# ------------------ Agent card ------------------

alice_skills = [
    AgentSkill(
        id='number_guess_evaluator',
        name='Number Guess Evaluator',
        description='Evaluates numeric guesses (1-100) against a secret number and replies with guidance (higher/lower/correct).',
        tags=['game', 'demo'],
        input_modes=['text/plain'],
        output_modes=['text/plain'],
        examples=['50'],
    )
]

alice_card = AgentCard(
    name='AgentAlice',
    description='Hosts the number-guessing game by picking a secret number and grading guesses.',
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC',
            url=f'http://localhost:{AGENT_ALICE_PORT}/a2a/v1',
            protocol_version='1.0',
        )
    ],
    version='1.0.0',
    capabilities=AgentCapabilities(
        streaming=False,
        push_notifications=False,
    ),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    skills=alice_skills,
)

# ------------------ Internal helpers ------------------


class NumberGuessExecutor(AgentExecutor):
    """AgentExecutor implementing the number-guessing logic directly."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle a newly received message from a peer agent."""
        raw_text = get_message_text(context.message) if context.message else ''
        response_text = process_guess(raw_text)

        # Tell the client that the task has started (a Task in the submitted
        # state must be the first event), then publish the answer and finally
        # mark it completed so Bob sees a full Task object with the artifact
        # attached.
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.add_artifact([Part(text=response_text)])
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
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
