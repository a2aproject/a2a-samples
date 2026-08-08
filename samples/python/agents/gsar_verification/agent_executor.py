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


# Four real records, varied on purpose -- not one example repeated. Each
# fabrication below (see _HALLUCINATED_FIELD) misreports a *different*
# field, so the test set covers cabin+bags, destination, passenger name,
# and bag count in isolation, not one memorized failure pattern.
_DB = {
    'ZFA04Y': {
        'reservation_id': 'ZFA04Y',
        'passenger_name': 'Mei Chen',
        'origin': 'SFO',
        'destination': 'JFK',
        'cabin': 'economy',
        'baggage_allowance': 1,
    },
    'QRX88B': {
        'reservation_id': 'QRX88B',
        'passenger_name': 'Diego Ramirez',
        'origin': 'LAX',
        'destination': 'ORD',
        'cabin': 'business',
        'baggage_allowance': 2,
    },
    'KLM12P': {
        'reservation_id': 'KLM12P',
        'passenger_name': 'Aisha Bello',
        'origin': 'ATL',
        'destination': 'MIA',
        'cabin': 'first',
        'baggage_allowance': 3,
    },
    'WYN45T': {
        'reservation_id': 'WYN45T',
        'passenger_name': 'Tom Becker',
        'origin': 'SEA',
        'destination': 'DEN',
        'cabin': 'economy',
        'baggage_allowance': 0,
    },
}

# Which single field each hallucinating summary misreports, per reservation
# -- deliberately different across the set.
_HALLUCINATED_FIELD = {
    'ZFA04Y': 'cabin_and_bags',  # cabin upgraded, bag count inflated
    'QRX88B': 'destination',  # wrong arrival city
    'KLM12P': 'passenger_name',  # wrong traveler
    'WYN45T': 'baggage_only',  # bag count inflated, everything else correct
}

_MODE = os.environ.get('REMOTE_AGENT_MODE', 'honest')  # "honest" | "hallucinating"


def _honest_summary(record: dict) -> str:
    return (
        f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
        f'{record["cabin"]} class, {record["origin"]} to {record["destination"]}, '
        f'{record["baggage_allowance"]} checked bag(s) included.'
    )


def _hallucinated_summary(record: dict) -> str:
    kind = _HALLUCINATED_FIELD[record['reservation_id']]
    if kind == 'cabin_and_bags':
        return (
            f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
            f'business class, {record["origin"]} to {record["destination"]}, '
            f'3 checked bags included at no charge.'
        )
    if kind == 'destination':
        return (
            f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
            f'{record["cabin"]} class, {record["origin"]} to Denver, '
            f'{record["baggage_allowance"]} checked bag(s) included.'
        )
    if kind == 'passenger_name':
        return (
            f'Reservation {record["reservation_id"]} for Jordan Lee — '
            f'{record["cabin"]} class, {record["origin"]} to {record["destination"]}, '
            f'{record["baggage_allowance"]} checked bag(s) included.'
        )
    # baggage_only
    return (
        f'Reservation {record["reservation_id"]} for {record["passenger_name"]} — '
        f'{record["cabin"]} class, {record["origin"]} to {record["destination"]}, '
        f'2 checked bags included.'
    )


class ReservationLookupAgent:
    """Looks up a real reservation and reports it -- honestly or not."""

    async def invoke(self, reservation_id: str) -> tuple[dict, str]:
        """Looks up `reservation_id` and returns (real_record, summary)."""
        record = _DB.get(reservation_id.strip().upper())
        if record is None:
            return {}, f'No reservation found for {reservation_id!r}.'

        # Same real record, same real lookup either way -- only the
        # summary differs. Not a lookup failure; the true data was right
        # there in the artifact this same call returns.
        summary = (
            _hallucinated_summary(record) if _MODE == 'hallucinating' else _honest_summary(record)
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

        # The real evidence -- exactly what the lookup returned, and nothing
        # else. Deliberately NOT also publishing `summary` as its own
        # artifact: it's a copy of the exact claim being verified, not
        # independent evidence, and including it let the judge treat the
        # claim as self-confirming on one case in a broader test (see
        # test_gsar_verification.py) -- a real methodological bug this
        # sample's own dataset expansion caught, not a hypothetical one.
        await task_updater.add_artifact(
            parts=[new_text_part(text=json.dumps(record), media_type='application/json')],
            name='reservation_record',
        )

        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(summary),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported by this example agent."""
        raise NotImplementedError('Cancel is not supported.')
