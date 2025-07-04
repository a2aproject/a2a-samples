from google.adk.agents import Agent
from google.adk.tools import google_search


root_agent = Agent(
    name="content_planner_agent",
    model="gemini-2.5-flash",
    description=("Planning agent that creates a detailed and logical outline for a piece of content,"
                 "given a high-level description."),
    instruction=("You are an expert content planner. Your task is to create a detailed and logical outline for a piece"
                 "of content, given a high-level description."),
    tools=[google_search],
)
