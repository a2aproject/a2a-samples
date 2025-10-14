import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from a2ui_ext import a2ui_MIME_TYPE
from agent import RestaurantAgent


logger = logging.getLogger(__name__)


class RestaurantAgentExecutor(AgentExecutor):
    """Restaurant AgentExecutor Example."""

    def __init__(self, base_url: str):
        self.agent = RestaurantAgent(base_url=base_url)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = ''
        ui_event_part = None
        action = None

        if context.message and context.message.parts:
            logger.info(
                f'--- AGENT_EXECUTOR: Processing {len(context.message.parts)} message parts ---'
            )
            for i, part in enumerate(context.message.parts):
                if isinstance(part.root, DataPart):
                    if 'actionName' in part.root.data:
                        logger.info(
                            f'  Part {i}: Found a2ui UI ClientEvent payload.'
                        )
                        ui_event_part = part.root
                    else:
                        logger.info(
                            f'  Part {i}: DataPart (data: {part.root.data})'
                        )
                elif isinstance(part.root, TextPart):
                    logger.info(
                        f'  Part {i}: TextPart (text: {part.root.text})'
                    )
                else:
                    logger.info(
                        f'  Part {i}: Unknown part type ({type(part.root)})'
                    )

        if ui_event_part:
            event_data = ui_event_part.data
            logger.info(f'Received a2ui ClientEvent: {event_data}')
            action = event_data.get('actionName')
            ctx = event_data.get('resolvedContext', {})

            if action == 'book_restaurant':
                restaurant_name = ctx.get(
                    'restaurantName', 'Unknown Restaurant'
                )
                address = ctx.get('address', 'Address not provided')
                image_url = ctx.get('imageUrl', '')
                query = f'USER_WANTS_TO_BOOK: {restaurant_name}, Address: {address}, ImageURL: {image_url}'

            elif action == 'submit_booking':
                restaurant_name = ctx.get(
                    'restaurantName', 'Unknown Restaurant'
                )
                party_size = ctx.get('partySize', 'Unknown Size')
                reservation_time = ctx.get('reservationTime', 'Unknown Time')
                dietary_reqs = ctx.get('dietary', 'None')
                image_url = ctx.get('imageUrl', '')
                query = f'User submitted a booking for {restaurant_name} for {party_size} people at {reservation_time} with dietary requirements: {dietary_reqs}. The image URL is {image_url}'

            else:
                query = f'User submitted an event: {action} with data: {ctx}'
        else:
            logger.info(
                'No a2ui UI event part found. Falling back to text input.'
            )
            query = context.get_user_input()

        logger.info(f"--- AGENT_EXECUTOR: Final query for LLM: '{query}' ---")

        task = context.current_task

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in self.agent.stream(query, task.context_id):
            is_task_complete = item['is_task_complete']
            if not is_task_complete:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item['updates'], task.context_id, task.id
                    ),
                )
                continue

            final_state = (
                TaskState.completed
                if action == 'submit_booking'
                else TaskState.input_required
            )

            content = item['content']
            final_parts = []
            if '---a2ui_JSON---' in content:
                logger.info('Splitting final response into text and UI parts.')
                text_content, json_string = content.split('---a2ui_JSON---', 1)

                if text_content.strip():
                    final_parts.append(
                        Part(root=TextPart(text=text_content.strip()))
                    )

                if json_string.strip():
                    try:
                        json_string_cleaned = (
                            json_string.strip()
                            .lstrip('```json')
                            .rstrip('```')
                            .strip()
                        )
                        json_data = json.loads(json_string_cleaned)

                        if 'gulfuiMessages' in json_data and isinstance(
                            json_data['gulfuiMessages'], list
                        ):
                            logger.info(
                                f'Found {len(json_data["gulfuiMessages"])} messages. Creating individual DataParts.'
                            )
                            for message in json_data['gulfuiMessages']:
                                final_parts.append(
                                    Part(
                                        root=DataPart(
                                            data=message,
                                            mime_type=a2ui_MIME_TYPE,
                                        )
                                    )
                                )
                        else:
                            logger.warning(
                                "Could not find 'gulfuiMessages' list, sending the object as a single DataPart."
                            )
                            final_parts.append(
                                Part(
                                    root=DataPart(
                                        data=json_data,
                                        mime_type=a2ui_MIME_TYPE,
                                    )
                                )
                            )

                    except json.JSONDecodeError as e:
                        logger.error(f'Failed to parse UI JSON: {e}')
                        final_parts.append(
                            Part(root=TextPart(text=json_string))
                        )
            else:
                final_parts.append(Part(root=TextPart(text=content.strip())))

            logger.info('--- FINAL PARTS TO BE SENT ---')
            for i, part in enumerate(final_parts):
                logger.info(f'  - Part {i}: Type = {type(part.root)}')
                if isinstance(part.root, TextPart):
                    logger.info(f'    - Text: {part.root.text[:200]}...')
                elif isinstance(part.root, DataPart):
                    logger.info(f'    - Data: {str(part.root.data)[:200]}...')
            logger.info('-----------------------------')

            await updater.update_status(
                final_state,
                new_agent_parts_message(final_parts, task.context_id, task.id),
                final=(final_state == TaskState.completed),
            )
            break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
