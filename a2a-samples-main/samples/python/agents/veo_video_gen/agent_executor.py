import logging

from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    FilePart,
    FileWithUri,
    Part,
    Task,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from agent import VideoGenerationAgent


logger = logging.getLogger(__name__)


class VideoGenerationAgentExecutor(AgentExecutor):
    """Video Generation AgentExecutor."""

    def __init__(self):
        self.agent = VideoGenerationAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        if not query:
            logger.warning('No user input found in context.')
            return

        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.contextId)

        logger.info(
            f"Executing VideoGenerationAgent for task {task.id} with query: '{query}'"
        )

        async for item in self.agent.stream(query, task.contextId):
            progress_percent = item.get('progress_percent')
            progress_float = (
                float(progress_percent / 100.0)
                if progress_percent is not None
                else None
            )

            if not item.get('is_task_complete', False):
                updates_text = item.get('updates', 'Processing...')
                progress_percent = item.get('progress_percent')
                progress_float = (
                    float(progress_percent / 100.0)
                    if progress_percent is not None
                    else None
                )

                agent_update_message = new_agent_text_message(
                    updates_text, task.contextId, task.id
                )

                logger.debug(
                    f'Task {task.id}: Updating status to WORKING. '
                    f"message_text='{updates_text}', "
                    f'intended_progress_float={progress_float * 100 if progress_float is not None else "N/A"} (note: progress arg not supported by update_status in this SDK version)'
                )
                try:
                    await updater.update_status(
                        TaskState.working, message=agent_update_message
                    )
                    logger.debug(
                        f'Task {task.id}: Successfully called updater.update_status(TaskState.working).'
                    )

                except Exception as e_update:
                    logger.error(
                        f'Task {task.id}: ERROR during updater.update_status: {e_update}',
                        exc_info=True,
                    )
                    raise
                continue
            logger.info(
                f'Task {task.id} marked complete by agent. Item: {item}'
            )
            final_message_text = item.get(
                'final_message_text', item.get('content', 'Task finished.')
            )
            final_message_obj = new_agent_text_message(
                final_message_text, task.contextId, task.id
            )

            if 'file_part_data' in item:
                file_data = item['file_part_data']

                artifact_name = item.get('artifact_name', 'generated_video')
                # Ensure artifact name has an extension if possible from mimeType
                if '.' not in artifact_name and 'mimeType' in file_data:
                    extension = file_data['mimeType'].split('/')[-1]
                    if (
                        extension and len(extension) < 5
                    ):  # basic check for valid extension
                        artifact_name = f'{artifact_name}.{extension}'

                artifact_description = item.get(
                    'artifact_description', 'Generated video file.'
                )

                file_with_uri = FileWithUri(
                    uri=file_data['uri'], mimeType=file_data['mimeType']
                )
                video_file_part = FilePart(
                    file=file_with_uri,
                    name=artifact_name,
                    description=artifact_description,
                )

                logger.info(
                    f'Task {task.id} completed with file. Artifact: {artifact_name}, URI: {file_data["uri"]}'
                )
                await updater.add_artifact([Part(root=video_file_part)])
                await updater.complete(
                    final_message_obj
                )  # Pass message positionally, remove progress

            else:  # No file part, completion is text-based (e.g., error or informational)
                is_error = item.get('is_error', False)
                final_task_state = (
                    TaskState.failed if is_error else TaskState.completed
                )
                logger.info(
                    f'Task {task.id} completed text-based. State: {final_task_state}, Message: {final_message_text}'
                )

                await updater.update_status(
                    final_task_state,
                    final_message_obj,
                    final=True,  # Marks task as completed/failed in the updater
                )
            break  # Stop processing after the first final item from agent stream

    @override
    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        # VEO operations might be cancellable via their API.
        # For this example, we keep it simple.
        logger.warning(
            f'Cancel operation requested for task {request.current_task.id if request.current_task else "unknown"}. Not supported by this agent version.'
        )
        raise ServerError(
            error=UnsupportedOperationError(
                message='Video generation cancellation is not supported.'
            )
        )
