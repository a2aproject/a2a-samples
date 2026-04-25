"""Governed file agent executor.

Demonstrates three AI Design Blueprint governance principles using A2A primitives:

| Blueprint Principle                              | A2A Primitive Used                        |
|--------------------------------------------------|-------------------------------------------|
| Explicit approval before destructive action (P8) | TASK_STATE_INPUT_REQUIRED — pause + resume|
| Perceptible background work (P5)                 | TaskStatusUpdateEvent WORKING per step    |
| Mid-task steering — cancellation (P7)            | cancel() handler + non-confirm abort path |
"""

from a2a.helpers import new_task_from_user_message, new_text_artifact, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types.a2a_pb2 import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)


class GovernedFileAgent(AgentExecutor):
    """File agent that enforces Blueprint governance on every destructive action."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input().strip()

        # Always enqueue the task first — SDK requires it as the first event.
        # On resume, reset state to WORKING to clear the old INPUT_REQUIRED status
        # so the server does not return early with the stale interrupted state.
        task = context.current_task or new_task_from_user_message(context.message)
        task.status.CopyFrom(TaskStatus(state=TaskState.TASK_STATE_WORKING))
        await event_queue.enqueue_event(task)

        if context.current_task is None:
            # ── First call: request approval before destructive action (Blueprint P8) ──
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.TASK_STATE_INPUT_REQUIRED,
                        message=new_text_message(
                            "This will permanently delete the requested file. "
                            "Reply 'confirm' to proceed or anything else to abort."
                        ),
                    ),
                )
            )
            return  # Pause — wait for user response.

        # ── Resume: check confirmation (Blueprint P7) ──
        if "confirm" not in user_input.lower():
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.TASK_STATE_CANCELED,
                        message=new_text_message(
                            "Action aborted — no confirmation received. File was not modified."
                        ),
                    ),
                )
            )
            return

        # ── Confirmed: stream progress (Blueprint P5) ──
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_text_message("Confirmed. Validating target path..."),
                ),
            )
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_text_message("Executing file deletion..."),
                ),
            )
        )

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=new_text_artifact(name="result", text="File deleted successfully."),
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
        """Mid-task steering: honour operator-level cancellation (Blueprint P7)."""
        task = context.current_task or new_task_from_user_message(context.message)
        task.status.CopyFrom(TaskStatus(state=TaskState.TASK_STATE_WORKING))
        await event_queue.enqueue_event(task)

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_CANCELED,
                    message=new_text_message(
                        "Cancelled by operator before execution — file was not modified."
                    ),
                ),
            )
        )
