import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm


def create_calendar_event(event_details: dict) -> dict:
    """Create a calendar event with the provided details."""
    # This function would contain logic to create a calendar event.
    # For now, we will just return a mock response.
    return {
        'status': 'success',
        'message': f"Event '{event_details['title']}' created successfully.",
    }


LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.5-flash-lite')
root_agent = Agent(
    name='calendar_agent',
    model=LiteLlm(model=LITELLM_MODEL),
    description=('Agent to manage calendar events.'),
    instruction=('You are a helpful agent who can manage calendar events.'),
    tools=[create_calendar_event],
)
