from a2a.types import AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card

# Define a skill - a specific capability your agent offers
# Agents can have multiple skills for different tasks
weather_agent_skill = AgentSkill(
    # Unique identifier for this skill
    id="weather_search",
    name="Search weather",
    # Detailed description helps clients understand when to use this skill
    description="Helps with weather in city, or states",
    # Tags for categorization and discovery
    # These help in agent marketplaces or registries
    tags=["weather"],
    # Examples show clients what kinds of requests work well
    # This is especially helpful for LLM-based clients
    examples=[
        "weather in LA, CA",
    ],
    # Optional: specify input/output modes
    # Default is text, but could include images, files, etc.
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)

# Use the helper function to create a complete Agent Card
weather_agent_card = create_agent_card(
    agent_name="Weather Agent",
    description="A helpful assistant agent that can answer questions.",
    skills=[weather_agent_skill],
)
