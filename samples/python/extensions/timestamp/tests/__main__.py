import os

import uvicorn

from a2a.helpers import (
    new_task_from_user_message,
    new_text_artifact,
    new_text_message,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from starlette.applications import Starlette
from timestamp_ext.core import TimestampExtension
from timestamp_ext.server import wrap_executor


_AGENT_URL = 'http://127.0.0.1:9998'


class EchoExecutor(AgentExecutor):
    """Emits one artifact then completes."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the task by echoing a text artifact and completing."""
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_text_message('working...'),
                ),
            )
        )
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=new_text_artifact(name='result', text='hello!'),
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the execution of the task."""
        raise NotImplementedError


if __name__ == '__main__':
    # Support fixed clock for deterministic E2E testing
    fixed_ts = os.environ.get('TIMESTAMP_EXT_FIXED_CLOCK')
    if fixed_ts is not None:
        ext = TimestampExtension(now_fn=lambda: float(fixed_ts))
    else:
        ext = TimestampExtension()

    card = ext.add_to_card(
        AgentCard(
            name='Echo',
            description='echo agent that demonstrates the timestamp extension',
            version='1.0.0',
            default_input_modes=['text'],
            default_output_modes=['text'],
            capabilities=AgentCapabilities(streaming=True),
            supported_interfaces=[
                AgentInterface(
                    protocol_binding='JSONRPC',
                    url=_AGENT_URL,
                    protocol_version='1.0',
                )
            ],
        )
    )

    handler = DefaultRequestHandler(
        agent_executor=wrap_executor(executor=EchoExecutor(), ext=ext),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = []
    routes.extend(create_agent_card_routes(card))
    routes.extend(create_jsonrpc_routes(handler, rpc_url='/'))

    app = Starlette(routes=routes)

    uvicorn.run(app, host='127.0.0.1', port=9998)
