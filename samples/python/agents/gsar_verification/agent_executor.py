"""A remote A2A agent that looks up a reservation and reports it back.

Correctly in one mode, with a fabricated detail in the other. Both modes
issue the exact same real lookup and return the exact same real artifact;
only the agent's own summary differs. This is the gap GSAR exists to catch,
reproduced across a real A2A network boundary instead of within one process.

Pattern (AgentExecutor, TaskUpdater, artifacts) follows a2a-samples' own
helloworld example -- the transport is the same real a2a-sdk any other
sample in that repo uses.
"""

from __future__ import annotations

import json
import os

from typing import TYPE_CHECKING

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState


if TYPE_CHECKING:
    from a2a.server.events import EventQueue


# A real record, exactly as the agent's own lookup would return it -- not
# invented for the purpose of catching a mistake, this IS the ground truth
# both modes below are given.
_DB = {
    'ZFA04Y': {
        'reservation_id': 'ZFA04Y',
        'passenger_name': 'Mei Chen',
        'origin': 'SFO',
        'destination': 'JFK',
        'cabin': 'economy',
        'baggage_allowance': 1,
    }
}

_MODE = os.environ.get('REMOTE_AGENT_MODE', 'honest')  # "honest" | "hallucinating"


class ReservationLookupAgent:
    """Looks up a real reservation and reports it -- honestly or not."""

    async def invoke(self, reservation_id: str) -> tuple[dict, str]:
        """Looks up `reservation_id` and returns (real_record, summary)."""
        record = _DB.get(reservation_id.strip().upper())
        if record is None:
            return {}, f'No reservation found for {reservation_id!r}.'

        if _MODE == 'hallucinating':
            # Same real record, same real lookup -- the summary just doesn't
            # match it. This is not a lookup failure; the data was right
            # there in the artifact this same call returns.
            summary = (
                f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
                f'business class, {record["origin"]} to {record["destination"]}, '
                f'3 checked bags included at no charge.'
            )
        else:
            summary = (
                f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
                f'{record["cabin"]} class, {record["origin"]} to {record["destination"]}, '
                f'{record["baggage_allowance"]} checked bag included.'
            )
        return record, summary


class ReservationLookupAgentExecutor(AgentExecutor):
    """AgentExecutor wiring, same shape as a2a-samples' own helloworld."""

    def __init__(self) -> None:
        self.agent = ReservationLookupAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Looks up the requested reservation and reports real evidence + summary."""
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue, task_id=task.id, context_id=task.context_id
        )
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message('Looking up reservation...'),
        )

        reservation_id = get_message_text(context.message) or ''
        record, summary = await self.agent.invoke(reservation_id)

        # The real evidence -- exactly what the lookup returned, as a
        # structured artifact alongside the natural-language summary.
        await task_updater.add_artifact(
            parts=[new_text_part(text=json.dumps(record), media_type='application/json')],
            name='reservation_record',
        )
        await task_updater.add_artifact(
            parts=[new_text_part(text=summary, media_type='text/plain')], name='summary'
        )

        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(summary),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported by this example agent."""
        raise NotImplementedError('Cancel is not supported.')
