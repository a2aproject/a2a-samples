from google.adk.agents import Agent
from google.adk.tools import google_search


root_agent = Agent(
    name="facts_agent",
    model="gemini-2.5-flash-lite-preview-06-17",
    description=("Agent to give interesting facts."),
    instruction=("You are a helpful agent who can provide interesting facts."),
    tools=[google_search],
)
