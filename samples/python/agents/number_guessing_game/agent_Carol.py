"""agent_Carol.py
AgentCarol – helper agent that visualises or shuffles Bob's guess history.

Carol receives plain-text JSON payloads from AgentBob and returns either
(1) a human-readable table of the guesses so far or (2) a JSON list with
entries randomly shuffled, depending on the request.  This functionality
is intentionally simple to keep the focus on A2A message flow.
"""

import json
import random
import uuid

from typing import Any

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentCard, Part, TextPart
from a2a.utils.message import get_message_text
from config import AGENT_CAROL_PORT
from utils import try_parse_json
from utils.game_logic import process_history_payload
from utils.server import run_agent_blocking


# ------------------ Agent card ------------------

carol_skills = [
    {
        'id': 'history_visualiser',
        'name': 'Guess History Visualiser',
        'description': 'Generates a formatted text summary of guess/response history to aid the player.',
        'tags': ['visualisation', 'demo'],
        'inputModes': ['text/plain'],
        'outputModes': ['text/plain'],
        'examples': ['[{"guess": 25, "response": "Go higher"}]'],
    },
    {
        'id': 'history_shuffler',
        'name': 'Guess History Shuffler',
        'description': 'Randomly shuffles the order of guess/response entries in a provided history list and returns JSON.',
        'tags': ['shuffling', 'demo'],
        'inputModes': ['text/plain'],
        'outputModes': ['text/plain'],
        'examples': [
            '{"action": "shuffle", "history": [{"guess": 25, "response": "Go higher"}]}'
        ],
    },
]

carol_card = AgentCard.model_validate(
    {
        'name': 'AgentCarol',
        'description': 'Visualises the history of guesses and hints from AgentAlice in a readable table format.',
        'url': f'http://localhost:{AGENT_CAROL_PORT}/a2a/v1',
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
        'skills': carol_skills,
    }
)

# ------------------ SDK AgentExecutor implementation ------------------


class HistoryHelperExecutor(AgentExecutor):
    """AgentExecutor implementing Carol's visualise / shuffle functionality."""

    @staticmethod
    def _print_guesses(label: str, history: list[dict[str, Any]]) -> None:
        """Utility: print only the numeric guesses in *history* for debugging."""
        try:
            guesses = [int(item.get('guess', '?')) for item in history]
        except Exception:
            guesses = []
        print(f'[Carol] {label}: {guesses}')

    def __init__(self) -> None:
        # Keep the last history list so we can reshuffle it on follow-up.
        self._last_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helper methods
    # ------------------------------------------------------------------

    async def _handle_followup(
        self, context: RequestContext, raw_text: str, event_queue: EventQueue
    ) -> None:
        """Handle a follow-up message that references an existing task."""
        task_id = context.task_id or (
            context.message.reference_task_ids[0]  # type: ignore[index]
            if context.message and context.message.reference_task_ids
            else str(uuid.uuid4())
        )
        updater = TaskUpdater(
            event_queue,
            task_id=task_id,
            context_id=context.context_id or str(uuid.uuid4()),
        )

        if raw_text.lower().startswith('well done'):
            print('[Carol] Received well done – completing task')
            await updater.complete()
            return

        # Any other text → shuffle again and ask for more input
        print('[Carol] Shuffling again and returning list')
        random.shuffle(self._last_history)
        # Debug print before sending back to Bob
        self._print_guesses('Shuffled list', self._last_history)
        response_text = json.dumps(self._last_history)
        await updater.add_artifact([Part(root=TextPart(text=response_text))])
        # Ask for another input and signal that this is the last event for this invocation
        await updater.requires_input(final=True)

    async def _handle_initial(
        self, raw_text: str, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Handle the first message in a new conversation."""
        response_text = (
            process_history_payload(raw_text) if raw_text else 'Invalid input.'
        )

        # Remember history list if provided so we can shuffle again later
        success, parsed = try_parse_json(raw_text)
        if (
            success
            and isinstance(parsed, dict)
            and parsed.get('action') == 'shuffle'
        ):
            hist = parsed.get('history', [])
            if isinstance(hist, list):
                self._last_history = hist

        task_id = context.task_id or str(uuid.uuid4())
        updater = TaskUpdater(
            event_queue,
            task_id=task_id,
            context_id=context.context_id or str(uuid.uuid4()),
        )
        # Debug print before sending initial response
        try:
            if success and isinstance(parsed, list):
                self._print_guesses('Initial list', parsed)
            else:
                self._print_guesses('Initial list', self._last_history)
        except Exception:
            pass
        await updater.add_artifact([Part(root=TextPart(text=response_text))])
        # Ask Bob for further input
        await updater.requires_input(final=True)

    # ------------------------------------------------------------------
    # AgentExecutor interface
    # ------------------------------------------------------------------

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Process an incoming message and dispatch to the appropriate handler."""
        raw_text = get_message_text(context.message) if context.message else ''
        is_followup = bool(
            context.message and context.message.reference_task_ids
        )

        if is_followup:
            await self._handle_followup(context, raw_text, event_queue)
        else:
            await self._handle_initial(raw_text, context, event_queue)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the ongoing task on explicit request from a peer agent."""
        if context.task_id:
            print(
                f'[Carol] Task {context.task_id} canceled on request of peer agent'
            )
            updater = TaskUpdater(
                event_queue,
                task_id=context.task_id,
                context_id=context.context_id or str(uuid.uuid4()),
            )
            await updater.cancel()


if __name__ == '__main__':
    run_agent_blocking(
        name='AgentCarol',
        port=AGENT_CAROL_PORT,
        agent_card=carol_card,
        executor=HistoryHelperExecutor(),
    )
