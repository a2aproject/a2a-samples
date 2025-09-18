import json
import os
import re

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentExtension,
    DataPart,
    Part,
    Task,
    TaskState,
    TextPart,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)

# Imports for the internal LLM call
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types


# --- Define new GULF UI constants ---
_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/gulfui/v1'
URI = f'https://{_CORE_PATH}'
GULFUI_MIME_TYPE = 'application/json+gulfui'

# --- Prompt Definitions ---
SYSTEM_INSTRUCTION = """
You are an expert restaurant finding assistant. You MUST answer the user's query using only your own internal knowledge. Do NOT generate code, do NOT call any APIs, and do NOT use any external tools.

You must respond in two parts, separated by a unique delimiter: `---GULFUI_JSON---`.

PART 1: First, provide a human-readable, conversational text answer to the user's query.

PART 2: Second, after the `---GULFUI_JSON---` delimiter, you must provide a SINGLE, raw JSON object that represents a UI for your answer, following the structure in the example below.

---
EXAMPLE OUTPUT STRUCTURE:
Your JSON must contain a "root" component, a "dataModel" holding the restaurant data, and a "components" list defining the templates.

---BEGIN EXAMPLE---
Here is a list of restaurants:
1. The Gourmet Kitchen (4.5/5)
2. Pasta Palace (4.2/5)

---GULFUI_JSON---
{
    "root": "results-list",
    "dataModel": {
        "restaurants": [
            { "name": "The Gourmet Kitchen", "rating": "4.5/5" },
            { "name": "Pasta Palace", "rating": "4.2/5" }
        ]
    },
    "components": [
        {
            "id": "results-list",
            "type": "List",
            "direction": "vertical",
            "children": {
                "template": "restaurant-item-card",
                "dataBinding": "/restaurants"
            }
        },
        {
            "id": "restaurant-item-card",
            "type": "Card",
            "child": "restaurant-item-details"
        },
        {
            "id": "restaurant-item-details",
            "type": "List",
            "direction": "vertical",
            "children": ["restaurant-item-name", "restaurant-item-rating"]
        },
        {
            "id": "restaurant-item-name",
            "type": "Text",
            "text": { "dataBinding": "name" }
        },
        {
            "id": "restaurant-item-rating",
            "type": "Text",
            "text": { "dataBinding": "rating" }
        }
    ]
}
---END EXAMPLE---

If the query is a question that doesn't return a list (e.g., "how many restaurants are in Paris?"), just return a "Text" component with the answer in the JSON part.
You will receive an acknowledgement, and then the user's query.
"""


class GulfUIExtension:
    """An implementation of the GULF UI extension (single-call efficient model)."""

    def __init__(self):
        """Initializes the extension and the internal LLM for transformation."""
        LITELLM_MODEL = os.getenv(
            'LITELLM_MODEL', 'gemini/gemini-2.0-flash-001'
        )
        self._llm = LiteLlm(model=LITELLM_MODEL)

    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=URI,
            description='Provides a declarative GULF UI JSON structure in messages.',
        )

    def activate(self, context: RequestContext) -> bool:
        """Checks if the GULF UI extension was requested by the client.
        If yes, it activates it so the server can confirm activation in its response.
        """
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap an executor to intercept the execute call."""
        return _GulfUIExecutor(executor, self)


class _GulfUIExecutor(AgentExecutor):
    """Executor wrapper that intercepts the execute() call.
    It checks if the GULF UI extension is active.
    - If YES, it runs its own "smart" logic (single LLM call for Text+JSON).
    - If NO, it delegates the call to the original, simple text-only executor.
    """

    def __init__(self, delegate: AgentExecutor, ext: GulfUIExtension):
        self._delegate = delegate
        self._ext = ext

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        query = context.get_user_input()
        if not query:
            return

        if self._ext.activate(context):
            await self._run_gulf_ui_logic(context, event_queue, query)
        else:
            print('\n--- GULF UI EXTENSION *NOT* ACTIVE ---')
            print('--- Running simple text-only delegate agent ---\n')
            await self._delegate.execute(context, event_queue)

    async def _run_gulf_ui_logic(
        self, context: RequestContext, event_queue: EventQueue, query: str
    ) -> None:
        """Our new "smart" logic that runs for UI-capable clients.
        This makes ONE LLM call to get both text and JSON.
        """
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        await updater.update_status(
            TaskState.working,
            new_agent_text_message(
                'Finding restaurants and building UI...',
                task.context_id,
                task.id,
            ),
        )

        print('\n--- GULF UI EXTENSION ACTIVATED ---')

        try:
            contents_list = [
                genai_types.Content(
                    role='user',
                    parts=[genai_types.Part.from_text(text=SYSTEM_INSTRUCTION)],
                ),
                genai_types.Content(
                    role='model',
                    parts=[
                        genai_types.Part.from_text(
                            text="Understood. I will provide the user's answer in two parts, separated by the delimiter as requested."
                        )
                    ],
                ),
                genai_types.Content(
                    role='user', parts=[genai_types.Part.from_text(text=query)]
                ),
            ]

            print(
                f'SENDING CHAT HISTORY TO LLM (History has {len(contents_list)} turns):'
            )
            for i, content_part in enumerate(contents_list):
                text_preview = (
                    content_part.parts[0].text.replace('\n', ' ')[0:200] + '...'
                )
                print(
                    f'  [{i + 1}] ROLE: {content_part.role}\n      TEXT: "{text_preview}"'
                )
            print('--------------------------')

            # The function returns an async_generator. We must await the first item from it.
            response_generator = self._ext._llm.generate_content_async(
                contents_list
            )
            response = await response_generator.__anext__()

            full_response_text = response.text

            print(
                f'RECEIVED RAW LLM RESPONSE:\n{full_response_text}\n--------------------------'
            )

            text_part_content = full_response_text
            json_data = None

            parts = re.split(
                r'\n---\s*GULFUI_JSON\s*---\n', full_response_text, maxsplit=1
            )

            if len(parts) == 2:
                text_part_content = parts[0].strip()
                json_text = (
                    parts[1].strip().lstrip('```json').rstrip('```').strip()
                )

                print('Successfully split response into TEXT and JSON parts.')

                try:
                    json_data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    print(
                        f'!!! FAILED TO PARSE JSON, sending text only. Error: {e}'
                    )
                    text_part_content = (
                        f'{text_part_content}\n(Failed to generate UI view)'
                    )
            else:
                print(
                    '!!! LLM response did not contain UI delimiter. Sending text only.'
                )

            message_parts = [Part(root=TextPart(text=text_part_content))]

            if json_data:
                message_parts.append(
                    Part(
                        root=DataPart(
                            data=json_data, mime_type=GULFUI_MIME_TYPE
                        )
                    )
                )

            await updater.update_status(
                TaskState.completed,
                new_agent_parts_message(
                    message_parts, task.context_id, task.id
                ),
                final=True,
            )

        except Exception as e:
            print(f'\n!!! Unhandled exception in UI logic. FULL ERROR: {e!r}')
            import traceback

            traceback.print_exc()  # Print the full stack trace

            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(
                    f'An error occurred: {e}', task.context_id, task.id
                ),
                final=True,
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        return await self._delegate.cancel(context, event_queue)


__all__ = [
    'GULFUI_MIME_TYPE',
    'URI',
    'GulfUIExtension',
]
