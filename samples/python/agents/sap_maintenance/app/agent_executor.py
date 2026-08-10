"""A2A SDK integration — bridges the PEOS agent with the A2A protocol."""

from __future__ import annotations

import json
import logging

from typing import TYPE_CHECKING

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    DataPart,
    Part,
    TaskState,
    TextPart,
)

from app.agent import SAPMaintenanceAgent


if TYPE_CHECKING:
    from a2a.server.events import EventQueue


logger = logging.getLogger(__name__)


class SAPMaintenanceAgentExecutor(AgentExecutor):
    """A2A AgentExecutor for the SAP Maintenance Order agent.

    Bridges the PEOS agent graph with the A2A protocol:
    - Converts A2A messages to agent queries
    - Streams PEOS responses as A2A task updates
    - Maps agent status to A2A TaskState
    - Emits structured DataParts for chart data and quick replies
    """

    def __init__(self) -> None:
        self.agent = SAPMaintenanceAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle an A2A task execution request."""
        query = self._extract_query(context)
        context_id = context.context_id or 'default'

        logger.info(
            'A2A execute: context_id=%s query=%s', context_id, query[:100]
        )

        async for event in self.agent.stream(query, context_id):
            is_complete = event.get('is_task_complete', False)
            needs_input = event.get('require_user_input', False)
            content = event.get('content', '')

            # Parse structured response
            parts = self._build_parts(content)

            if needs_input:
                state = TaskState.input_required
            elif is_complete:
                state = TaskState.completed
            else:
                state = TaskState.working

            await event_queue.enqueue_event(
                state=state,
                parts=parts,
            )

    def _extract_query(self, context: RequestContext) -> str:
        """Extract user text from the A2A request context."""
        message = context.message
        if message and message.parts:
            for part in message.parts:
                if hasattr(part, 'root') and isinstance(part.root, TextPart):
                    return part.root.text
                if isinstance(part, TextPart):
                    return part.text
        return ''

    def _build_parts(self, content: str) -> list[Part]:
        """Convert agent response to A2A Parts (TextPart + DataParts).

        Response format:
        - parts[0]: TextPart — markdown answer text
        - parts[1]: DataPart — chart data (optional)
        - parts[2]: DataPart — quick replies
        """
        # Try parsing as structured JSON
        try:
            payload = json.loads(content)
            answer = payload.get('answer', content)
            chart_data = payload.get('chartData', [])
            quick_replies = payload.get('quickReplies', [])
        except (json.JSONDecodeError, TypeError):
            answer = content
            chart_data = []
            quick_replies = []

        parts: list[Part] = [
            Part(root=TextPart(text=answer)),
        ]

        # Chart data as DataPart
        if chart_data:
            parts.append(Part(root=DataPart(data={'items': chart_data})))

        # Quick replies as DataPart
        if quick_replies:
            qr_items = [
                {'title': qr, 'value': qr}
                for qr in quick_replies
                if isinstance(qr, str)
            ]
            parts.append(Part(root=DataPart(data={'items': qr_items})))

        return parts
