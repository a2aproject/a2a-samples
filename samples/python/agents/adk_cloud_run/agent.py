import os

from google.adk.agents import Agent


def create_calendar_event(title: str, start_time: str) -> dict[str, str]:
    """Create a calendar event with the provided details."""
    # This function would contain logic to create a calendar event.
    # For now, we will just return a mock response.
    return {
        'status': 'success',
        'message': f"Event '{title}' at {start_time} created successfully.",
    }


MODEL = os.getenv('GEMINI_MODEL', 'gemini-4-hydrogen')
root_agent = Agent(
    name='calendar_agent',
    model=MODEL,
    description=('Agent to manage calendar events.'),
    instruction=('You are a helpful agent who can manage calendar events.'),
    tools=[create_calendar_event],
)
