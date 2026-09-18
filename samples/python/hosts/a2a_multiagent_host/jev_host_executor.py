"""A host executor that lets Jev pick the remote agent and forwards the message to it.

Selected with ``HOST_ROUTER=jev`` or ``--router jev``. The default ``llm`` router, the ADK
Gemini agent in ``routing_agent.py``, is untouched. This executor makes no LLM call: Jev
answers "which agent" from the remote Agent Cards, the user's message goes to that agent
over A2A, and the agent's artifacts and status come back on the host's task. The decision
itself travels back too, as a ``routing`` artifact, so a client can see the probabilities,
the confidence and what the call cost.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from typing import TYPE_CHECKING

import httpx

from a2a.client import A2ACardResolver
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    DataPart,
    Message,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import get_message_text, new_task
from a2a.utils.errors import ServerError
from jev_router import JevRouter
from remote_agent_connection import RemoteAgentConnections


if TYPE_CHECKING:
    from a2a.server.events import EventQueue


logger = logging.getLogger(__name__)

NO_AGENT_TEXT = 'No remote agent covers this request.'


class JevRoutingExecutor(AgentExecutor):
    """Route with Jev, forward over A2A, relay the result."""

    def __init__(
        self,
        router: JevRouter,
        cards: list[AgentCard],
        connections: dict[str, RemoteAgentConnections] | None = None,
    ) -> None:
        self.router = router
        self.cards = {card.name: card for card in cards}
        self.connections = connections or {
            card.name: RemoteAgentConnections(agent_card=card, agent_url=card.url) for card in cards
        }
        # A follow-up in the same context goes back to the agent that asked for it.
        self._agent_for_context: dict[str, str] = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Pick an agent (or reuse the one waiting for input), forward, relay."""
        if context.message is None:
            raise ServerError(error=UnsupportedOperationError())
        task = context.current_task or new_task(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        text = get_message_text(context.message)

        agent_name = self._agent_for_context.pop(task.context_id, None)
        if agent_name is None:
            try:
                route = await self.router.route(text, self.cards.values())
            except Exception as e:  # noqa: BLE001 - surface the reason on the task
                logger.warning('jev routing failed: %s', e)
                await updater.failed(_text_message(updater, f'Routing failed: {e}'))
                return
            await updater.add_artifact(
                [Part(root=DataPart(data={'route': route.as_dict()}))], name='routing'
            )
            if route.agent_name is None:
                await updater.complete(_text_message(updater, NO_AGENT_TEXT))
                return
            agent_name = route.agent_name

        request = SendMessageRequest(
            id=uuid.uuid4().hex,
            params=MessageSendParams.model_validate(
                {
                    'message': {
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': text}],
                        'messageId': uuid.uuid4().hex,
                        'contextId': task.context_id,
                    }
                }
            ),
        )
        try:
            response = await self.connections[agent_name].send_message(request)
        except Exception as e:  # noqa: BLE001
            await updater.failed(_text_message(updater, f'{agent_name} unreachable: {e}'))
            return
        if not isinstance(response.root, SendMessageSuccessResponse):
            await updater.failed(
                _text_message(updater, f'{agent_name} error: {response.root.error.message}')
            )
            return

        result = response.root.result
        if isinstance(result, Message):
            await updater.add_artifact(result.parts, name=agent_name)
            await updater.complete()
            return
        await self._relay(result, agent_name, task.context_id, updater)

    async def _relay(
        self, remote: Task, agent_name: str, context_id: str, updater: TaskUpdater
    ) -> None:
        for artifact in remote.artifacts or []:
            await updater.add_artifact(artifact.parts, name=artifact.name or agent_name)
        status_message = (
            _text_message(updater, get_message_text(remote.status.message))
            if remote.status.message
            else None
        )
        state = remote.status.state
        if state == TaskState.input_required:
            self._agent_for_context[context_id] = agent_name
            await updater.requires_input(status_message)
        elif state == TaskState.failed:
            await updater.failed(status_message)
        else:
            await updater.complete(status_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported, same as the LLM host."""
        raise ServerError(error=UnsupportedOperationError())


def _text_message(updater: TaskUpdater, text: str) -> Message:
    return updater.new_agent_message([Part(root=TextPart(text=text))])


async def resolve_card(client: httpx.AsyncClient, address: str) -> AgentCard | None:
    """Fetch one Agent Card, or log and return ``None`` so one dead agent does not stop the host."""
    try:
        return await A2ACardResolver(client, address).get_agent_card()
    except Exception as e:  # noqa: BLE001
        logger.warning('no agent card at %s: %s', address, e)
        return None


async def resolve_cards(addresses: list[str]) -> list[AgentCard]:
    """Fetch the Agent Card of every reachable address."""
    async with httpx.AsyncClient(timeout=30) as client:
        cards = [await resolve_card(client, address) for address in addresses]
    return [card for card in cards if card is not None]


def create_jev_executor(addresses: list[str]) -> JevRoutingExecutor:
    """Build the executor from the environment: ``TYPESAFE_API_KEY`` is required."""
    api_key = os.getenv('TYPESAFE_API_KEY')
    if not api_key:
        raise ValueError(
            'TYPESAFE_API_KEY environment variable not set (needed for HOST_ROUTER=jev).'
        )
    router = JevRouter(
        api_key=api_key,
        model=os.getenv('SYSTEM_ONE_MODEL', 'jev-latest'),
        base_url=os.getenv('SYSTEM_ONE_BASE_URL', 'https://api.typesafe.ai'),
        timeout=float(os.getenv('SYSTEM_ONE_TIMEOUT', '15')),
    )
    cards = asyncio.run(resolve_cards(addresses))
    if not cards:
        raise ValueError('no remote agent cards could be resolved')
    logger.info('jev router: %s', ', '.join(f'{c.name} ({len(c.skills)} skills)' for c in cards))
    return JevRoutingExecutor(router, cards)
