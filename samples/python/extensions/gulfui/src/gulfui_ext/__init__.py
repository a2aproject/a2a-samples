import json
import os
import re

from typing import Any

from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    AgentExtension,
    DataPart,
    Message,
    Part,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)

# Import the specific agent type so our wrapper can interact with it
from agent import RestaurantAgent


# --- Define new GULF UI constants ---
_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/gulfui/v1'
URI = f'https://{_CORE_PATH}'
GULFUI_MIME_TYPE = 'application/json+gulfui'

# --- GULF UI SCHEMA ---
# The full schema definition
GULFUI_SCHEMA = """
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/ui-layout.schema.json",
    "title": "UI Layout",
    "description": "A schema for defining a UI layout composed of a hierarchy of components, a global style, and a shared data model.",
    "type": "object",
    "properties": {
        "root": { "$ref": "#/$defs/componentInstanceRef" },
        "components": { "type": "array", "items": { "$ref": "#/$defs/component" } },
        "globals": { "$ref": "#/$defs/style" },
        "dataModel": { "$ref": "#/$defs/dataModel" }
    },
    "required": ["root", "components"],
    "$defs": {
        "componentInstanceRef": { "type": "string" },
        "componentInstanceListRef": {
            "oneOf": [
                { "type": "array", "items": { "$ref": "#/$defs/componentInstanceRef" } },
                {
                    "type": "object",
                    "properties": {
                        "template": { "$ref": "#/$defs/componentInstanceRef" },
                        "dataBinding": { "$ref": "#/$defs/dataBinding" }
                    },
                    "required": ["template", "dataBinding"]
                }
            ]
        },
        "style": { "type": "object", "properties": { "primary_color": { "type": "string" }, "agent_logo": { "type": "string", "format": "uri" } } },
        "dataBinding": {
            "oneOf": [ { "type": "string" }, { "type": "number" }, { "type": "boolean" }, { "type": "object" }, { "type": "array" } ]
        },
        "action": {
            "type": "object",
            "properties": {
                "action": { "type": "string" },
                "staticContext": { "type": "object" },
                "dynamicContext": { "additionalProperties": { "$ref": "#/$defs/dataBinding" } }
            },
            "required": ["action"]
        },
        "dataModel": { "type": "object" },
        "componentType": { "enum": ["Text", "List", "Card", "Image", "AudioPlayer", "TextField", "MutuallyExclusiveMultipleChoice", "MultipleChoice", "Button", "Slider", "Tabs", "Divider", "Carousel"] },
        "component": {
            "type": "object",
            "properties": { "id": { "type": "string" }, "type": { "$ref": "#/$defs/componentType" } },
            "required": ["id", "type"],
            "oneOf": [
                { "properties": { "type": { "const": "Text" }, "text": { "type": "string" } }, "required": ["text"] },
                { "properties": { "type": { "const": "List" }, "direction": { "enum": ["vertical", "horizontal"] }, "children": { "$ref": "#/$defs/componentInstanceListRef" }, "distribution": { "enum": ["start", "center", "end"] }, "alignment": { "enum": ["start", "center", "end"] } }, "required": ["children"] },
                { "properties": { "type": { "const": "Card" }, "child": { "$ref": "#/$defs/componentInstanceRef" } }, "required": ["child"] },
                { "properties": { "type": { "const": "Image" }, "url": { "type": "string", "format": "uri" }, "fit": { "type": "string" }, "max_width": { "type": "number" }, "max_height": { "type": "number" } }, "required": ["url"] },
                { "properties": { "type": { "const": "AudioPlayer" }, "url": { "type": "string", "format": "uri" }, "description": { "type": "string" } }, "required": ["url"] },
                { "properties": { "type": { "const": "TextField" }, "description": { "type": "string" }, "inputType": { "enum": ["shortText", "number", "date", "longText"] }, "valueBinding": { "$ref": "#/$defs/dataBinding" } } },
                { "properties": { "type": { "const": "MutuallyExclusiveMultipleChoice" }, "options": { "type": "array", "items": { "type": "string" } }, "valueBinding": { "$ref": "#/$defs/dataBinding" } }, "required": ["options"] },
                { "properties": { "type": { "const": "MultipleChoice" }, "options": { "type": "array", "items": { "type": "string" } }, "valueBinding": { "$ref": "#/$defs/dataBinding" } }, "required": ["options"] },
                { "properties": { "type": { "const": "Button" }, "label": { "type": "string" }, "action": { "$ref": "#defs/action" } }, "required": ["label", "action"] },
                { "properties": { "type": { "const": "Slider" }, "min": { "type": "number" }, "max": { "type": "number" }, "step": { "type": "number" }, "valueBinding": { "$ref": "#/$defs/dataBinding" } } },
                { "properties": { "type": { "const": "Tabs" }, "tabItems": { "type": "array", "items": { "type": "object", "properties": { "label": { "type": "string" }, "child": { "$ref": "#/$defs/componentInstanceRef" } }, "required": ["label", "child"] } } }, "required": ["tabItems"] },
                { "properties": { "type": { "const": "Divider" } } },
                { "properties": { "type": { "const": "Carousel" }, "children": { "$ref": "#/$defs/componentInstanceListRef" } }, "required": ["children"] }
            ]
        }
    }
}
"""

# --- Prompt Definitions ---
# This is the "smart" instruction, now with the example from particletypes.ts included
# and a strict instruction to use the dataModel.
SMART_INSTRUCTION = f"""
You are an expert restaurant finding assistant. You MUST answer the user's query using only your own internal knowledge. Do NOT generate code, do NOT call any APIs, and do NOT use any external tools.

You must respond in two parts, separated by a unique delimiter: `---GULFUI_JSON---`.

PART 1: First, provide a human-readable, conversational text answer to the user's query.

PART 2: Second, after the `---GULFUI_JSON---` delimiter, you must provide a SINGLE, raw JSON object that represents the UI for your answer, strictly conforming to the schema below.

---
MANDATORY JSON STRUCTURE:
If your answer contains a list of items (like restaurants), you MUST put the data array inside the "dataModel" object and use a SINGLE template component with a "dataBinding" to render that list, as shown in the example. Do NOT hard-code a separate component for each item in the list.

---BEGIN EXAMPLE (from particletypes.ts)---
{{
    "root": "results-list",
    "dataModel": {{
        "restaurants": [
            {{ "name": "The Gourmet Kitchen", "rating": "4.5/5", "imageUrl": "https://placehold.co/img1" }},
            {{ "name": "Pasta Palace", "rating": "4.2/5", "imageUrl": "https://placehold.co/img2" }}
        ]
    }},
    "components": [
        {{
            "id": "results-list",
            "type": "List",
            "direction": "vertical",
            "children": {{
                "template": "restaurant-item-card",
                "dataBinding": "/restaurants"
            }}
        }},
        {{
            "id": "restaurant-item-card",
            "type": "Card",
            "child": "restaurant-item-details"
        }},
        {{
            "id": "restaurant-item-details",
            "type": "List",
            "direction": "vertical",
            "children": ["restaurant-item-name", "restaurant-item-rating"]
        }},
        {{
            "id": "restaurant-item-name",
            "type": "Text",
            "text": {{ "dataBinding": "name" }}
        }},
        {{
            "id": "restaurant-item-rating",
            "type": "Text",
            "text": {{ "dataBinding": "rating" }}
        }}
    ]
}}
---END EXAMPLE---

If the query is a simple text answer, just return a single "Text" component.

Here is the full schema to conform to:
<SCHEMA>
{GULFUI_SCHEMA}
</SCHEMA>
"""

# Store the original simple instruction from the agent.
ORIGINAL_AGENT_INSTRUCTION = RestaurantAgent()._agent.instruction


class GulfUIExtension:
    """An implementation of the GULF UI extension (Robust Model)."""

    def __init__(self):
        pass

    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=URI,
            description='Provides a declarative GULF UI JSON structure in messages.',
        )

    def activate(self, context: RequestContext) -> bool:
        """
        Checks if the GULF UI extension was requested by the client.
        """
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap an executor to intercept the execute call."""
        return _GulfUIExecutor(executor, self)


class _GulfUIExecutor(AgentExecutor):
    """
    Executor wrapper that intercepts the execute() call.
    It hijacks the agent's prompt, lets the ADK Runner work,
    and then parses the output.
    """

    def __init__(self, delegate: AgentExecutor, ext: GulfUIExtension):
        self._delegate = delegate  # The original RestaurantAgentExecutor
        self._ext = ext
        # Get the actual ADK LlmAgent object from inside the delegate's agent
        self._adk_agent = self._delegate.agent._agent

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        is_ui_active = self._ext.activate(context)

        try:
            if is_ui_active:
                # === HIJACK PROMPT ===
                print(
                    '\n--- GULF UI EXTENSION ACTIVATED: HIJACKING PROMPT (with full schema + example) ---'
                )
                self._adk_agent.instruction = SMART_INSTRUCTION

                # We must wrap the queue to intercept and parse the response
                wrapped_queue = _GulfUIEventQueue(event_queue, self._ext)
                await self._delegate.execute(context, wrapped_queue)

            else:
                # === UI NOT ACTIVE ===
                print('\n--- GULF UI EXTENSION *NOT* ACTIVE ---')
                print('--- Running simple text-only delegate agent ---\n')
                await self._delegate.execute(context, event_queue)

        finally:
            # CRITICAL: Always reset the agent's instruction to its original state
            if is_ui_active:
                print(
                    '--- GULF UI EXTENSION: Restoring original agent prompt ---'
                )
                self._adk_agent.instruction = ORIGINAL_AGENT_INSTRUCTION

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        return await self._delegate.cancel(context, event_queue)


class _GulfUIEventQueue(EventQueue):
    """
    An EventQueue decorator that intercepts the final COMPLETED event.
    It expects the text to contain our delimiter and parses it into two parts.
    """

    def __init__(self, delegate: EventQueue, ext: GulfUIExtension):
        self._delegate = delegate
        self._ext = ext

    async def enqueue_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        # We only care about the final, completed status update
        if (
            isinstance(event, TaskStatusUpdateEvent)
            and event.status.state == TaskState.completed
            and event.status.message
            and event.status.message.parts
        ):
            text_part = next(
                (p.root for p in event.status.message.parts if p.root.text),
                None,
            )

            if text_part:
                # The ADK Runner has run and given us the raw text, delimiter, and JSON
                # all in one text part. Now we split it.
                print(
                    f'RECEIVED RAW LLM RESPONSE FROM RUNNER:\n{text_part.text}\n--------------------------'
                )
                full_response_text = text_part.text
                json_data = None

                parts = re.split(
                    r'\n---\s*GULFUI_JSON\s*---\n',
                    full_response_text,
                    maxsplit=1,
                )

                if len(parts) == 2:
                    text_part_content = parts[0].strip()
                    json_text = (
                        parts[1].strip().lstrip('```json').rstrip('```').strip()
                    )

                    print(
                        'Successfully split response into TEXT and JSON parts.'
                    )

                    # Modify the original text part to contain ONLY the text
                    text_part.text = text_part_content

                    try:
                        json_data = json.loads(json_text)
                        # Add the new DataPart to the message's parts list
                        event.status.message.parts.append(
                            Part(
                                root=DataPart(
                                    data=json_data, mime_type=GULFUI_MIME_TYPE
                                )
                            )
                        )
                    except json.JSONDecodeError as e:
                        print(f'!!! FAILED TO PARSE JSON. Error: {e}')
                        # If parsing fails, just send the modified text part.
                        text_part.text = (
                            f'{text_part_content}\n(Failed to generate UI view)'
                        )
                else:
                    print(
                        '!!! LLM response did not contain UI delimiter. Sending text only.'
                    )

        # Pass the (now modified) event to the real queue.
        return await self._delegate.enqueue_event(event)

    # --- Delegate Methods ---
    async def dequeue_event(
        self, no_wait: bool = False
    ) -> Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent:
        return await self._delegate.dequeue_event(no_wait)

    async def close(self) -> None:
        return await self._delegate.close()

    def tap(self) -> EventQueue:
        return self._delegate.tap()

    def is_closed(self) -> bool:
        return self._delegate.is_closed()

    def task_done(self) -> None:
        return self._delegate.task_done()


__all__ = [
    'GULFUI_MIME_TYPE',
    'URI',
    'GulfUIExtension',
]
