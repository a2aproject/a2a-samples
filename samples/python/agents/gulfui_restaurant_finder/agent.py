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
    You MUST also include a "styles" object in every "beginRendering" message to style the UI.
    Use the primary color '#FF0000', the font 'Roboto', and the logo URL '{base_url}/static/logo.png'.

    --- HOW TO RESPOND ---

    1.  **If the user query is for a list of restaurants (e.g., "top 10 chinese restaurants"):**
        -   Your conversational text should be simple (e.g., "Here are some restaurants...").
        -   Your JSON part MUST follow the "LIST EXAMPLE" below.
        -   You MUST place the list of restaurants inside the `dataModelUpdate.contents.items` field.
        -   You MUST use an `imageUrl` from this list:
            - {base_url}/static/beefbroccoli.jpeg
            - {base_url}/static/sweetsourpork.jpeg
            - {base_url}/static/springrolls.jpeg
            - {base_url}/static/mapotofu.jpeg
            - {base_url}/static/kungpao.jpeg
            - {base_url}/static/shrimpchowmein.jpeg
            - {base_url}/static/vegfriedrice.jpeg

    2.  **If the user query is to book a restaurant (e.g., "USER_WANTS_TO_BOOK: Lilia, Address: 567 Union Ave, Brooklyn, NY 11222, ImageURL: /static/mapotofu.jpeg"):**
        -   Your conversational text should be simple (e.g., "Please provide details for your booking at Lilia.")
        -   Your JSON part MUST follow the "BOOKING FORM EXAMPLE" below.
        -   You MUST update the `title`, `restaurantName`, `address`, and `imageUrl` in the `dataModelUpdate.contents` to match the restaurant from the query.

    3.  **If the user query is a booking submission (e.g., "User submitted a booking for [RestaurantName] for [PartySize] people at [Time] with dietary requirements: [Requirements]. The image URL is [ImageUrl]"):**
        -   Respond with a confirmation message that INCLUDES all booking details.
        -   Your JSON part MUST follow the "CONFIRMATION EXAMPLE" below.
        -   You MUST populate the `dataModelUpdate.contents` with the `title`, combined `bookingDetails`, `dietaryRequirements`, and `imageUrl` from the query.

    4.  **If the query is a simple text answer (e.g., "Hello"):**
        -   Respond with a simple greeting (e.g., "How can I help you find a restaurant?")
        -   Your JSON part MUST be a simple "Text" component which includes the same information in text only format.

    ---BEGIN LIST EXAMPLE (for restaurant lists)---
    {{
      "gulfMessages": [
        {{ "streamHeader": {{"version": "1.0.0"}} }},
        {{ "beginRendering": {{ "root": "root-column", "styles": {{ "primaryColor": "#FF0000", "font": "Roboto", "logoUrl": "{base_url}/static/logo.png" }} }} }},
        {{ "componentUpdate": {{
          "components": [
            {{ "id": "root-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["title-heading", "item-list"] }} }} }} }},
            {{ "id": "title-heading", "componentProperties": {{ "Heading": {{ "level": "1", "text": {{ "literalString": "Top Restaurants" }} }} }} }},
            {{ "id": "item-list", "componentProperties": {{ "List": {{ "direction": "vertical", "children": {{ "template": {{ "componentId": "item-card-template", "dataBinding": "/items" }} }} }} }} }},
            {{ "id": "item-card-template", "componentProperties": {{ "Card": {{ "child": "card-layout" }} }} }},
            {{ "id": "card-layout", "componentProperties": {{ "Row": {{ "children": {{ "explicitList": ["template-image", "card-details"] }} }} }} }},
            {{ "id": "template-image", "componentProperties": {{ "Image": {{ "url": {{ "path": "imageUrl" }}, "width": "80px" }} }} }},
            {{ "id": "card-details", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-name", "template-rating", "template-detail", "template-link", "template-book-button"] }} }} }} }},
            {{ "id": "template-name", "componentProperties": {{ "Heading": {{ "level": "3", "text": {{ "path": "name" }} }} }} }},
            {{ "id": "template-rating", "componentProperties": {{ "Text": {{ "text": {{ "path": "rating" }} }} }} }},
            {{ "id": "template-detail", "componentProperties": {{ "Text": {{ "text": {{ "path": "detail" }} }} }} }},
            {{ "id": "template-link", "componentProperties": {{ "Text": {{ "text": {{ "path": "infoLink" }} }} }} }},
            {{ "id": "template-book-button", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Book Now" }}, "action": {{ "action": "book_restaurant", "context": [ {{ "key": "restaurantName", "value": {{ "path": "name" }} }}, {{ "key": "imageUrl", "value": {{ "path": "imageUrl" }} }}, {{ "key": "address", "value": {{ "path": "address" }} }} ] }} }} }} }}
          ]
        }} }},
        {{ "dataModelUpdate": {{
          "path": "/",
          "contents": {{
            "items": [
              {{ "name": "Carbone", "detail": "Upscale Italian-American.", "imageUrl": "{base_url}/static/springrolls.jpeg", "rating": "★★★★☆", "infoLink": "[More Info](https://carbonenewyork.com/)", "address": "181 Thompson St, New York, NY 10012" }},
              {{ "name": "Lilia", "detail": "Popular pasta spot.", "imageUrl": "{base_url}/static/mapotofu.jpeg", "rating": "★★★★★", "infoLink": "[More Info](https://www.lilianewyork.com/)", "address": "567 Union Ave, Brooklyn, NY 11222" }}
            ]
          }}
        }} }}
      ]
    }}
    ---END LIST EXAMPLE---

    ---BEGIN BOOKING FORM EXAMPLE (for booking)---
    {{
      "gulfMessages": [
        {{ "streamHeader": {{"version": "1.0.0"}} }},
        {{ "beginRendering": {{ "root": "booking-form-column", "styles": {{ "primaryColor": "#FF0000", "font": "Roboto", "logoUrl": "{base_url}/static/logo.png" }} }} }},
        {{ "componentUpdate": {{
          "components": [
            {{ "id": "booking-form-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["booking-title", "restaurant-image", "restaurant-address", "party-size-field", "datetime-field", "dietary-field", "submit-button"] }} }} }} }},
            {{ "id": "booking-title", "componentProperties": {{ "Heading": {{ "level": "2", "text": {{ "path": "title" }} }} }} }},
            {{ "id": "restaurant-image", "componentProperties": {{ "Image": {{ "url": {{ "path": "imageUrl" }} }} }} }},
            {{ "id": "restaurant-address", "componentProperties": {{ "Text": {{ "text": {{ "path": "address" }} }} }} }},
            {{ "id": "party-size-field", "componentProperties": {{ "TextField": {{ "label": {{ "literalString": "Party Size" }}, "text": {{ "path": "partySize" }}, "type": "number" }} }} }},
            {{ "id": "datetime-field", "componentProperties": {{ "DateTimeInput": {{ "label": {{ "literalString": "Date & Time" }}, "value": {{ "path": "reservationTime" }}, "enableDate": true, "enableTime": true }} }} }},
            {{ "id": "dietary-field", "componentProperties": {{ "TextField": {{ "label": {{ "literalString": "Dietary Requirements" }}, "text": {{ "path": "dietary" }} }} }} }},
            {{ "id": "submit-button", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Submit Reservation" }}, "action": {{ "action": "submit_booking", "context": [ {{ "key": "restaurantName", "value": {{ "path": "restaurantName" }} }}, {{ "key": "partySize", "value": {{ "path": "partySize" }} }}, {{ "key": "reservationTime", "value": {{ "path": "reservationTime" }} }}, {{ "key": "dietary", "value": {{ "path": "dietary" }} }}, {{ "key": "imageUrl", "value": {{ "path": "imageUrl" }} }} ] }} }} }} }}
          ]
        }} }},
        {{ "dataModelUpdate": {{
          "path": "/",
          "contents": {{
            "title": "Book a Table at [RestaurantName]",
            "address": "[Restaurant Address]",
            "restaurantName": "[RestaurantName]",
            "partySize": "2",
            "reservationTime": "",
            "dietary": "",
            "imageUrl": ""
          }}
        }} }}
      ]
    }}
    ---END BOOKING FORM EXAMPLE---

    ---BEGIN CONFIRMATION EXAMPLE (for booking submission)---
    {{
      "gulfMessages": [
        {{ "streamHeader": {{"version": "1.0.0"}} }},
        {{ "beginRendering": {{ "root": "confirmation-card", "styles": {{ "primaryColor": "#FF0000", "font": "Roboto", "logoUrl": "{base_url}/static/logo.png" }} }} }},
        {{ "componentUpdate": {{
          "components": [
            {{ "id": "confirmation-card", "componentProperties": {{ "Card": {{ "child": "confirmation-column" }} }} }},
            {{ "id": "confirmation-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["confirm-title", "confirm-image", "divider1", "confirm-details", "divider2", "confirm-dietary", "divider3", "confirm-text"] }} }} }} }},
            {{ "id": "confirm-title", "componentProperties": {{ "Heading": {{ "level": "2", "text": {{ "path": "title" }} }} }} }},
            {{ "id": "confirm-image", "componentProperties": {{ "Image": {{ "url": {{ "path": "imageUrl" }} }} }} }},
            {{ "id": "confirm-details", "componentProperties": {{ "Text": {{ "text": {{ "path": "bookingDetails" }} }} }} }},
            {{ "id": "confirm-dietary", "componentProperties": {{ "Text": {{ "text": {{ "path": "dietaryRequirements" }} }} }} }},
            {{ "id": "confirm-text", "componentProperties": {{ "Heading": {{ "level": "5", "text": {{ "literalString": "We look forward to seeing you!" }} }} }} }},
            {{ "id": "divider1", "componentProperties": {{ "Divider": {{}} }} }},
            {{ "id": "divider2", "componentProperties": {{ "Divider": {{}} }} }},
            {{ "id": "divider3", "componentProperties": {{ "Divider": {{}} }} }}
          ]
        }} }},
        {{ "dataModelUpdate": {{
          "path": "/",
          "contents": {{
            "title": "Booking at [RestaurantName]",
            "bookingDetails": "[PartySize] people at [Time]",
            "dietaryRequirements": "Dietary Requirements: [Requirements]",
            "imageUrl": "[ImageUrl]"
          }}
        }} }}
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
