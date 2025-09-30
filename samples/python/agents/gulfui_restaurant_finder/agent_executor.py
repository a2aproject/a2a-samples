import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Task,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from agent import RestaurantAgent


# Set up logging for this module
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

        if context.message and context.message.parts:
            # --- Logging Loop ---
            logger.info(
                f'--- AGENT_EXECUTOR: Processing {len(context.message.parts)} message parts ---'
            )
            for i, part in enumerate(context.message.parts):
                if isinstance(part.root, DataPart):
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
            # --- Main Logic Loop ---
            # Look for a part that looks like a GULF UI ClientEvent.
            for part in context.message.parts:
                # TEMP FIX: Instead of relying on a broken mime_type, we inspect the data directly.
                # If it's a DataPart with a dictionary inside that contains 'actionName',
                # we can be confident it's our UI event.
                if (
                    isinstance(part.root, DataPart)
                    and isinstance(part.root.data, dict)
                    and 'actionName' in part.root.data
                ):
                    logger.info(
                        'Found GULF UI ClientEvent payload by inspecting data.'
                    )
                    ui_event_part = part.root
                    break

        if ui_event_part:
            event_data = ui_event_part.data
            logger.info(f'Received GULF ClientEvent: {event_data}')
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
                'No GULF UI event part found. Falling back to text input.'
            )
            query = context.get_user_input()

        if not query:
            logger.warning(
                'Query for LLM is empty. Agent may fall back to a default response.'
            )

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

            await updater.update_status(
                TaskState.completed,
                new_agent_text_message(
                    item['content'], task.context_id, task.id
                ),
                final=True,
            )
            break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
