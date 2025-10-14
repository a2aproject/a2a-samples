import json
import logging
import os


logger = logging.getLogger(__name__)


def get_restaurants(cuisine: str, location: str, count: int = 5) -> str:
    """Call this tool to get a list of restaurants based on a cuisine and location.
    'count' is the number of restaurants to return.
    """
    logger.info(f'--- TOOL CALLED: get_restaurants (count: {count}) ---')
    logger.info(f'  - Cuisine: {cuisine}')
    logger.info(f'  - Location: {location}')

    items = []
    if 'new york' in location.lower() or 'ny' in location.lower():
        try:
            script_dir = os.path.dirname(__file__)
            file_path = os.path.join(script_dir, 'restaurant_data.json')
            with open(file_path) as f:
                all_items = json.load(f)

            # Slice the list to return only the requested number of items
            items = all_items[:count]
            logger.info(
                f'  - Success: Found {len(all_items)} restaurants, returning {len(items)}.'
            )

        except FileNotFoundError:
            logger.error(
                f'  - Error: restaurant_data.json not found at {file_path}'
            )
        except json.JSONDecodeError:
            logger.error(f'  - Error: Failed to decode JSON from {file_path}')

    return json.dumps(items)


def get_ui_instructions(base_url: str) -> str:
    """Call this tool to get the necessary instructions, templates, and schemas
    for generating a a2ui UI response. The LLM must use the output of this
    tool to structure its final answer.
    """
    logger.info('--- TOOL CALLED: get_ui_instructions ---')
    logger.info(f'  - Using base_url: {base_url}')

    return f"""
    You are a helpful restaurant finding assistant. Your final output MUST be a a2ui UI JSON response.

    To generate the response, you MUST follow these rules:
    1.  Your response MUST be in two parts, separated by the delimiter: `---a2ui_JSON---`.
    2.  The first part is your conversational text response.
    3.  The second part is a single, raw JSON object with one key, "a2uiMessages".

    --- UI TEMPLATE RULES ---
    -   If the query is for a list of restaurants, use the restaurant data you have already received from the `get_restaurants` tool to populate the `dataModelUpdate.contents.items` field.
    -   If the number of restaurants is 5 or fewer, you MUST use the `SINGLE_COLUMN_LIST_EXAMPLE` template.
    -   If the number of restaurants is more than 5, you MUST use the `TWO_COLUMN_LIST_EXAMPLE` template.
    -   If the query is to book a restaurant (e.g., "USER_WANTS_TO_BOOK..."), you MUST use the `BOOKING_FORM_EXAMPLE` template.
    -   If the query is a booking submission (e.g., "User submitted a booking..."), you MUST use the `CONFIRMATION_EXAMPLE` template.


    ---BEGIN SINGLE_COLUMN_LIST_EXAMPLE---
    {{
      "a2uiMessages": [
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
            "items": [] // Populate this with restaurant data
          }}
        }} }}
      ]
    }}
    ---END SINGLE_COLUMN_LIST_EXAMPLE---

    ---BEGIN TWO_COLUMN_LIST_EXAMPLE---
    {{
      "a2uiMessages": [
        {{ "streamHeader": {{"version": "1.0.0"}} }},
        {{ "beginRendering": {{ "root": "root-column", "styles": {{ "primaryColor": "#FF0000", "font": "Roboto", "logoUrl": "{base_url}/static/logo.png" }} }} }},
        {{ "componentUpdate": {{
          "components": [
            {{ "id": "root-column", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["title-heading", "restaurant-row-1"] }} }} }} }},
            {{ "id": "title-heading", "componentProperties": {{ "Heading": {{ "level": "1", "text": {{ "literalString": "Top Restaurants" }} }} }} }},
            {{ "id": "restaurant-row-1", "componentProperties": {{ "Row": {{ "children": {{ "explicitList": ["item-card-1", "item-card-2"] }} }} }} }},
            {{ "id": "item-card-1", "weight": 1, "componentProperties": {{ "Card": {{ "child": "card-layout-1" }} }} }},
            {{ "id": "card-layout-1", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-image-1", "card-details-1"] }} }} }} }},
            {{ "id": "template-image-1", "componentProperties": {{ "Image": {{ "url": {{ "path": "/items/0/imageUrl" }}, "width": "100%" }} }} }},
            {{ "id": "card-details-1", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-name-1", "template-rating-1", "template-detail-1", "template-link-1", "template-book-button-1"] }} }} }} }},
            {{ "id": "template-name-1", "componentProperties": {{ "Heading": {{ "level": "3", "text": {{ "path": "/items/0/name" }} }} }} }},
            {{ "id": "template-rating-1", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/0/rating" }} }} }} }},
            {{ "id": "template-detail-1", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/0/detail" }} }} }} }},
            {{ "id": "template-link-1", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/0/infoLink" }} }} }} }},
            {{ "id": "template-book-button-1", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Book Now" }}, "action": {{ "action": "book_restaurant", "context": [ {{ "key": "restaurantName", "value": {{ "path": "/items/0/name" }} }}, {{ "key": "imageUrl", "value": {{ "path": "/items/0/imageUrl" }} }}, {{ "key": "address", "value": {{ "path": "/items/0/address" }} }} ] }} }} }} }},
            {{ "id": "item-card-2", "weight": 1, "componentProperties": {{ "Card": {{ "child": "card-layout-2" }} }} }},
            {{ "id": "card-layout-2", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-image-2", "card-details-2"] }} }} }} }},
            {{ "id": "template-image-2", "componentProperties": {{ "Image": {{ "url": {{ "path": "/items/1/imageUrl" }}, "width": "100%" }} }} }},
            {{ "id": "card-details-2", "componentProperties": {{ "Column": {{ "children": {{ "explicitList": ["template-name-2", "template-rating-2", "template-detail-2", "template-link-2", "template-book-button-2"] }} }} }} }},
            {{ "id": "template-name-2", "componentProperties": {{ "Heading": {{ "level": "3", "text": {{ "path": "/items/1/name" }} }} }} }},
            {{ "id": "template-rating-2", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/1/rating" }} }} }} }},
            {{ "id": "template-detail-2", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/1/detail" }} }} }} }},
            {{ "id": "template-link-2", "componentProperties": {{ "Text": {{ "text": {{ "path": "/items/1/infoLink" }} }} }} }},
            {{ "id": "template-book-button-2", "componentProperties": {{ "Button": {{ "label": {{ "literalString": "Book Now" }}, "action": {{ "action": "book_restaurant", "context": [ {{ "key": "restaurantName", "value": {{ "path": "/items/1/name" }} }}, {{ "key": "imageUrl", "value": {{ "path": "/items/1/imageUrl" }} }}, {{ "key": "address", "value": {{ "path": "/items/1/address" }} }} ] }} }} }} }}
          ]
        }} }},
        {{ "dataModelUpdate": {{
          "path": "/",
          "contents": {{
            "items": [] // Populate this with restaurant data
          }}
        }} }}
      ]
    }}
    ---END TWO_COLUMN_LIST_EXAMPLE---

    ---BEGIN BOOKING_FORM_EXAMPLE---
    {{
      "a2uiMessages": [
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
    ---END BOOKING_FORM_EXAMPLE---

    ---BEGIN CONFIRMATION_EXAMPLE---
    {{
      "a2uiMessages": [
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
    ---END CONFIRMATION_EXAMPLE---
    """
