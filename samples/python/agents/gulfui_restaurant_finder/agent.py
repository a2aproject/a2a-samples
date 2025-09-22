import os

from collections.abc import AsyncIterable
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


TEXT_ONLY_INSTRUCTION = """
    You are a helpful restaurant finding assistant.
    Respond to the user's request clearly and concisely.
    If the user asks for a booking, ask them for the party size and reservation time.
    If the user provides booking details, confirm the booking.
"""

GULF_UI_INSTRUCTION_TEMPLATE = """
    You are a helpful restaurant finding assistant.
    You MUST respond with both a text part and a GULF UI JSON part,
    following the delimiter rules provided in the instructions that follow this prompt.

    --- HOW TO RESPOND ---

    1.  **If the user query is for a list of restaurants (e.g., "top 10 chinese restaurants"):**
        -   Your conversational text should be simple (e.g., "Here are some restaurants...").
        -   Your JSON part MUST follow the "LIST EXAMPLE" below.
        -   You MUST place the list of restaurants inside the `contents.items` field.
        -   You MUST use an `imageUrl` from this list:
            - {base_url}/static/beefbroccoli.jpeg
            - {base_url}/static/sweetsourpork.jpeg
            - {base_url}/static/springrolls.jpeg
            - {base_url}/static/mapotofu.jpeg
            - {base_url}/static/kungpao.jpeg
            - {base_url}/static/shrimpchowmein.jpeg
            - {base_url}/static/vegfriedrice.jpeg

    2.  **If the user query is to book a restaurant (e.g., "USER_WANTS_TO_BOOK: Lilia"):**
        -   Your conversational text should be simple (e.g., "Please provide details for your booking at Lilia.")
        -   Your JSON part MUST follow the "BOOKING FORM EXAMPLE" below.
        -   You MUST update the `title` and `restaurantName` in the `DataModelUpdate` `contents` to match the restaurant from the query.

    3.  **If the user query is a booking submission (e.g., "User submitted a booking for [RestaurantName] for [PartySize] people at [Time]"):**
        -   Respond with a confirmation message that INCLUDES the restaurant name, party size, and time (e.g., "Your table for [PartySize] at [RestaurantName] is confirmed for [Time]!").
        -   Your JSON part MUST follow the "CONFIRMATION EXAMPLE" below.
        -   You MUST populate the `contents` in the `DataModelUpdate` with the `restaurantName`, `partySize`, and `reservationTime` from the query.

    4.  **If the query is a simple text answer (e.g., "Hello"):**
        -   Respond with a simple greeting (e.g., "How can I help you find a restaurant?")
        -   Your JSON part MUST be a simple "Text" component.

    ---BEGIN LIST EXAMPLE (for restaurant lists)---
    {{
      "gulfMessages": [
        {{ "root": "root-column" }},
        {{
          "components": [
            {{ "id": "root-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["title-heading", "item-list"] }} }} }} }},
            {{ "id": "title-heading", "componentProperties": {{ "Heading": {{ "level": "1", "text": {{ "literalString": "Example List Title" }} }} }} }},
            {{ "id": "item-list", "componentProperties": {{ "List": {{ "direction": "vertical", "children": {{ "template": {{ "componentId": "item-card-template", "dataBinding": "/items" }} }} }} }} }},
            {{ "id": "item-card-template", "componentProperties": {{ "Card": {{ "child": "card-details" }} }} }},
            {{ "id": "card-details", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-image", "template-name", "template-detail", "template-book-button"] }} }} }} }},
            {{ "id": "template-image", "componentProperties": {{ "Image": {{ "url": {{ "path": "imageUrl" }} }} }} }},
            {{ "id": "template-name", "componentProperties": {{ "Text": {{ "text": {{ "path": "name" }} }} }} }},
            {{ "id": "template-detail", "componentProperties": {{ "Text": {{ "text": {{ "path": "detail" }} }} }} }},
            {{ "id": "template-book-button", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Book Now" }}, "action": {{ "action": "book_restaurant", "context": [ {{ "key": "restaurantName", "value": {{ "path": "name" }} }} ] }} }} }} }}
          ]
        }},
        {{
          "path": "/",
          "contents": {{
            "items": [
              {{ "name": "Example Item 1", "detail": "Detail for item 1", "imageUrl": "{base_url}/static/springrolls.jpeg" }},
              {{ "name": "Example Item 2", "detail": "Detail for item 2", "imageUrl": "{base_url}/static/mapotofu.jpeg" }}
            ]
          }}
        }}
      ]
    }}
    ---END LIST EXAMPLE---

    ---BEGIN BOOKING FORM EXAMPLE (for booking)---
    {{
      "gulfMessages": [
        {{ "root": "booking-form-column" }},
        {{
          "components": [
            {{ "id": "booking-form-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["booking-title", "party-size-field", "datetime-field", "submit-button"] }} }} }} }},
            {{ "id": "booking-title", "componentProperties": {{ "Heading": {{ "level": "2", "text": {{ "path": "title" }} }} }} }},
            {{ "id": "party-size-field", "componentProperties": {{ "TextField": {{ "label": {{ "literalString": "Party Size" }}, "text": {{ "path": "partySize" }}, "type": "number" }} }} }},
            {{ "id": "datetime-field", "componentProperties": {{ "DateTimeInput": {{ "value": {{ "path": "reservationTime" }}, "enableDate": true, "enableTime": true }} }} }},
            {{ "id": "submit-button", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Submit Reservation" }}, "action": {{ "action": "submit_booking", "context": [ {{ "key": "restaurantName", "value": {{ "path": "restaurantName" }} }}, {{ "key": "partySize", "value": {{ "path": "partySize" }} }}, {{ "key": "reservationTime", "value": {{ "path": "reservationTime" }} }} ] }} }} }} }}
          ]
        }},
        {{
          "path": "/",
          "contents": {{
            "title": "Book a Table at [RestaurantName]",
            "restaurantName": "[RestaurantName]",
            "partySize": "2",
            "reservationTime": ""
          }}
        }}
      ]
    }}
    ---END BOOKING FORM EXAMPLE---

    ---BEGIN CONFIRMATION EXAMPLE (for booking submission)---
    {{
      "gulfMessages": [
        {{ "root": "confirmation-column" }},
        {{
          "components": [
            {{ "id": "confirmation-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["confirm-title", "confirm-restaurant", "confirm-party", "confirm-time", "confirm-text"] }} }} }} }},
            {{ "id": "confirm-title", "componentProperties": {{ "Heading": {{ "level": "2", "text": {{ "literalString": "Booking Confirmed!" }} }} }} }},
            {{ "id": "confirm-restaurant", "componentProperties": {{ "Text": {{ "text": {{ "path": "restaurantName" }} }} }} }},
            {{ "id": "confirm-party", "componentProperties": {{ "Text": {{ "text": {{ "path": "partySize" }} }} }} }},
            {{ "id": "confirm-time", "componentProperties": {{ "Text": {{ "text": {{ "path": "reservationTime" }} }} }} }},
            {{ "id": "confirm-text", "componentProperties": {{ "Text": {{ "text": {{ "literalString": "We look forward to seeing you!" }} }} }} }}
          ]
        }},
        {{
          "path": "/",
          "contents": {{
            "restaurantName": "[RestaurantName]",
            "partySize": "[PartySize] people",
            "reservationTime": "at [Time]"
          }}
        }}
      ]
    }}
    ---END CONFIRMATION EXAMPLE---
"""


class RestaurantAgent:
    """An agent that finds restaurants based on user criteria."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self, base_url: str):
        self._agent = self._build_agent(base_url=base_url)
        self._user_id = 'remote_agent'
        self.gulf_ui_instruction = GULF_UI_INSTRUCTION_TEMPLATE.format(
            base_url=base_url
        )
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def get_processing_message(self) -> str:
        return 'Finding restaurants that match your criteria...'

    def _build_agent(self, base_url: str) -> LlmAgent:
        """Builds the LLM agent for the restaurant agent."""
        LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini-2.5-flash')

        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='restaurant_agent',
            description=(
                'This agent finds restaurants based on user criteria like cuisine,'
                ' location, or rating.'
            ),
            instruction=TEXT_ONLY_INSTRUCTION,
            tools=[],
        )

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ''
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = '\n'.join(
                        [p.text for p in event.content.parts if p.text]
                    )

                yield {
                    'is_task_complete': True,
                    'content': response,
                }
            else:
                yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                }
