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
_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/gulfui/v7'
URI = f'https://{_CORE_PATH}'
GULFUI_MIME_TYPE = 'application/json+gulfui'

# --- GULF UI 7.0 SCHEMAS ---
# These schemas are based on the GULF 7.0 specification.

SCHEMA_BEGIN_RENDERING = """
{
  "title": "BeginRendering Message",
  "description": "Signals that the UI can now be rendered and provides initial root component and styling information.",
  "type": "object",
  "properties": {
    "root": {
      "type": "string",
      "description": "The ID of the root component from which rendering should begin. This property is REQUIRED."
    },
    "styles": {
      "type": "object",
      "description": "An object containing styling information for the UI.",
      "properties": {
        "font": {"type": "string"},
        "logoUrl": {"type": "string"},
        "primaryColor": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}
      }
    }
  },
  "required": ["root"]
}
"""

SCHEMA_COMPONENT_UPDATE = """
{
  "title": "ComponentUpdate Message",
  "description": "A schema for a ComponentUpdate message in the A2A streaming UI protocol.",
  "type": "object",
  "properties": {
    "components": {
      "type": "array",
      "description": "A flat list of all component instances available for rendering. This property is REQUIRED.",
      "items": {
        "description": "A specific instance of a ComponentType with its own unique ID and properties.",
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "description": "A unique identifier for this component instance. This property is REQUIRED."
          },
          "componentProperties": {
            "type": "object",
            "description": "Defines the properties for a specific component type. Exactly ONE of the properties in this object must be set.",
            "properties": {
              "Heading": {
                "type": "object",
                "properties": {
                  "text": {
                    "type": "object",
                    "properties": {
                      "path": {"type": "string"},
                      "literalString": {"type": "string"}
                    }
                  },
                  "level": {"type": "string", "enum": ["1", "2", "3", "4", "5"]}
                },
                "required": ["text"]
              },
              "Text": {
                "type": "object",
                "properties": {
                  "text": {
                    "type": "object",
                    "properties": {
                      "path": {"type": "string"},
                      "literalString": {"type": "string"}
                    }
                  }
                },
                "required": ["text"]
              },
              "Image": {
                "type": "object",
                "properties": {
                  "url": {
                    "type": "object",
                    "properties": {
                      "path": {"type": "string"},
                      "literalString": {"type": "string"}
                    }
                  }
                },
                "required": ["url"]
              },
              "Video": {
                "type": "object",
                "properties": {"url": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}}},
                "required": ["url"]
              },
              "AudioPlayer": {
                "type": "object",
                "properties": {
                  "url": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "description": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}}
                },
                "required": ["url"]
              },
              "Row": {
                "type": "object",
                "properties": {
                  "children": {"type": "object", "properties": {"explicitList": {"type": "array", "items": {"type": "string"}}, "template": {"type": "object", "properties": {"componentId": {"type": "string"}, "dataBinding": {"type": "string"}}, "required": ["componentId", "dataBinding"]}}},
                  "distribution": {"type": "string", "enum": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"]},
                  "alignment": {"type": "string", "enum": ["start", "center", "end", "stretch"]}
                },
                "required": ["children"]
              },
              "Column": {
                "type": "object",
                "properties": {
                  "children": {"type": "object", "properties": {"explicitList": {"type": "array", "items": {"type": "string"}}, "template": {"type": "object", "properties": {"componentId": {"type": "string"}, "dataBinding": {"type": "string"}}, "required": ["componentId", "dataBinding"]}}},
                  "distribution": {"type": "string", "enum": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"]},
                  "alignment": {"type": "string", "enum": ["start", "center", "end", "stretch"]}
                },
                "required": ["children"]
              },
              "List": {
                "type": "object",
                "properties": {
                  "children": {"type": "object", "properties": {"explicitList": {"type": "array", "items": {"type": "string"}}, "template": {"type": "object", "properties": {"componentId": {"type": "string"}, "dataBinding": {"type": "string"}}, "required": ["componentId", "dataBinding"]}}},
                  "direction": {"type": "string", "enum": ["vertical", "horizontal"], "default": "vertical"},
                  "alignment": {"type": "string", "enum": ["start", "center", "end", "stretch"]}
                },
                "required": ["children"]
              },
              "Card": {
                "type": "object",
                "properties": {"child": {"type": "string"}},
                "required": ["child"]
              },
              "Tabs": {
                "type": "object",
                "properties": {
                  "tabItems": {"type": "array", "items": {"type": "object", "properties": {"title": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}}, "child": {"type": "string"}}, "required": ["title", "child"]}}
                },
                "required": ["tabItems"]
              },
              "Divider": {
                "type": "object",
                "properties": {
                  "axis": {"type": "string", "enum": ["horizontal", "vertical"], "default": "horizontal"},
                  "color": {"type": "string"},
                  "thickness": {"type": "number", "default": 1}
                }
              },
              "Modal": {
                "type": "object",
                "properties": {"entryPointChild": {"type": "string"}, "contentChild": {"type": "string"}},
                "required": ["entryPointChild", "contentChild"]
              },
              "Button": {
                "type": "object",
                "properties": {
                  "label": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "action": {
                    "type": "object",
                    "properties": {
                      "action": {"type": "string"},
                      "context": {"type": "array", "items": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}, "literalNumber": {"type": "number"}, "literalBoolean": {"type": "boolean"}}}}, "required": ["key", "value"]}}
                    },
                    "required": ["action"]
                  }
                },
                "required": ["label", "action"]
              },
              "CheckBox": {
                "type": "object",
                "properties": {
                  "label": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "value": {"type": "object", "properties": {"path": {"type": "string"}, "literalBoolean": {"type": "boolean"}}}
                },
                "required": ["label", "value"]
              },
              "TextField": {
                "type": "object",
                "properties": {
                  "text": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "label": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "type": {"type": "string", "enum": ["shortText", "number", "date", "longText"]},
                  "validationRegexp": {"type": "string"}
                },
                "required": ["label"]
              },
              "DateTimeInput": {
                "type": "object",
                "properties": {
                  "value": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}},
                  "enableDate": {"type": "boolean", "default": true},
                  "enableTime": {"type": "boolean", "default": false},
                  "outputFormat": {"type": "string"}
                },
                "required": ["value"]
              },
              "MultipleChoice": {
                "type": "object",
                "properties": {
                  "selections": {"type": "object", "properties": {"path": {"type": "string"}, "literalArray": {"type": "array", "items": {"type": "string"}}}},
                  "options": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "object", "properties": {"path": {"type": "string"}, "literalString": {"type": "string"}}}, "value": {"type": "string"}}, "required": ["label", "value"]}},
                  "maxAllowedSelections": {"type": "integer", "default": 1}
                },
                "required": ["selections"]
              },
              "Slider": {
                "type": "object",
                "properties": {
                  "value": {"type": "object", "properties": {"path": {"type": "string"}, "literalNumber": {"type": "number"}}},
                  "minValue": {"type": "number", "default": 0},
                  "maxValue": {"type": "number", "default": 100}
                },
                "required": ["value"]
              }
            }
          }
        },
        "required": ["id", "componentProperties"]
      }
    }
  },
  "required": ["components"]
}
"""

SCHEMA_DATA_MODEL_UPDATE = """
{
  "title": "Data model update",
  "description": "Sets or replaces the data model at a specified path with new content.",
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "An optional path to a location within the data model. If omitted, the entire data model will be replaced."
    },
    "contents": {
      "description": "The JSON content to be placed at the specified path. This property is REQUIRED."
    }
  },
  "required": [
    "contents"
  ]
}
"""

# --- Generic Prompt Suffix ---
# This constant contains ONLY the generic instructions for formatting the output
# according to the GULF 7.0 protocol.
GENERIC_UI_INSTRUCTION_SUFFIX = f"""
---
Your response MUST be in two parts, separated by a unique delimiter: `---GULFUI_JSON---`.

PART 1: First, provide your complete human-readable, conversational text answer as normal.

PART 2: Second, after the `---GULFUI_JSON---` delimiter, you must provide a SINGLE, raw JSON **OBJECT**.
This root OBJECT must contain a single key named "gulfMessages".
The value of "gulfMessages" must be a JSON **ARRAY** containing the messages needed to render the UI for your answer, in the following order:
1.  A `BeginRendering` message.
2.  A `ComponentUpdate` message (containing ALL components needed).
3.  A `DataModelUpdate` message (populating the data model with the data from your answer).

---
MANDATORY JSON STRUCTURE (GULF 7.0):
You MUST follow the new component structure which uses a "componentProperties" object to wrap the properties for each component type (e.g., "componentProperties": {{"Text": {{"text": ...}}}}).
If your answer contains a list of items (like restaurants), you MUST place this list inside the `contents` field of the `DataModelUpdate` message (with path "/") and use a templated `List` to render them.

---BEGIN EXAMPLE (GULF 7.0 structure wrapped in the required object)---
{{
  "gulfMessages": [
    {{
      "root": "root-column"
    }},
    {{
      "components": [
        {{
          "id": "root-column",
          "componentProperties": {{
            "Column": {{
              "children": {{
                "explicitList": ["title-heading", "item-list"]
              }}
            }}
          }}
        }},
        {{
          "id": "title-heading",
          "componentProperties": {{
            "Heading": {{
              "level": "1",
              "text": {{ "literalString": "Example List Title" }}
            }}
          }}
        }},
        {{
          "id": "item-list",
          "componentProperties": {{
            "List": {{
              "direction": "vertical",
              "children": {{
                "template": {{
                  "componentId": "item-card-template",
                  "dataBinding": "/items"
                }}
              }}
            }}
          }}
        }},
        {{
          "id": "item-card-template",
          "componentProperties": {{
            "Card": {{
              "child": "card-details"
            }}
          }}
        }},
        {{
          "id": "card-details",
          "componentProperties": {{
            "Column": {{
              "children": {{
                "explicitList": ["template-name", "template-detail"]
              }}
            }}
          }}
        }},
        {{
          "id": "template-name",
          "componentProperties": {{
            "Text": {{
              "text": {{ "path": "name" }}
            }}
          }}
        }},
        {{
          "id": "template-detail",
          "componentProperties": {{
            "Text": {{
              "text": {{ "path": "detail" }}
            }}
          }}
        }}
      ]
    }},
    {{
      "path": "/",
      "contents": {{
        "items": [
          {{ "name": "Example Item 1", "detail": "Detail for item 1" }},
          {{ "name": "Example Item 2", "detail": "Detail for item 2" }}
        ]
      }}
    }}
  ]
}}
---END EXAMPLE---

If the query is a simple text answer, just create a "Text" component using the same 3-message array structure inside the "gulfMessages" key.

Here are the full schemas your JSON messages MUST conform to:

<SCHEMA_BEGIN_RENDERING>
{SCHEMA_BEGIN_RENDERING}
</SCHEMA_BEGIN_RENDERING>

<SCHEMA_COMPONENT_UPDATE>
{SCHEMA_COMPONENT_UPDATE}
</SCHEMA_COMPONENT_UPDATE>

<SCHEMA_DATA_MODEL_UPDATE>
{SCHEMA_DATA_MODEL_UPDATE}
</SCHEMA_DATA_MODEL_UPDATE>
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
    It dynamically combines the agent's prompt with the UI instructions,
    lets the ADK Runner work, and then parses the output.
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
                # Dynamically combine the agent's specific instruction with our generic UI format instruction.
                original_instruction = self._adk_agent.instruction
                smart_instruction = (
                    f'{original_instruction}\n{GENERIC_UI_INSTRUCTION_SUFFIX}'
                )

                print(
                    '\n--- GULF UI EXTENSION ACTIVATED: HIJACKING PROMPT (GENERIC GULF 7.0) ---'
                )
                self._adk_agent.instruction = smart_instruction

                # Wrap the queue to intercept and parse the delimited response
                wrapped_queue = _GulfUIEventQueue(event_queue, self._ext)
                await self._delegate.execute(context, wrapped_queue)

            else:
                # Run the agent normally if the extension is not active
                print('\n--- GULF UI EXTENSION *NOT* ACTIVE ---')
                print('--- Running simple text-only delegate agent ---\n')
                await self._delegate.execute(context, event_queue)

        finally:
            # Always reset the agent's instruction to its original state
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
                        'Successfully split response into TEXT and JSON OBJECT parts.'
                    )

                    # Modify the original text part to contain ONLY the text
                    text_part.text = text_part_content

                    try:
                        json_data = json.loads(
                            json_text
                        )  # This should be a dict (object)

                        event.status.message.parts.append(
                            Part(
                                root=DataPart(
                                    data=json_data, mime_type=GULFUI_MIME_TYPE
                                )
                            )
                        )
                    except json.JSONDecodeError as e:
                        print(f'!!! FAILED TO PARSE JSON. Error: {e}')
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
