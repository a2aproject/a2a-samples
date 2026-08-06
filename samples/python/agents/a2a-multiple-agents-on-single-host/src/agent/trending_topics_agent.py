from a2a.types import AgentCard, AgentCapabilities, TransportProtocol, AgentSkill
from google.adk.agents import LlmAgent
from google.adk.tools import google_search


def get_trending_topics_agent(model: str) -> LlmAgent:
    return LlmAgent(
        model=model,
        name='trending_topics_agent',
        instruction="""
    You are a social media trends analyst. Your job is to search the web for current trending topics,
    particularly from social platforms.

    When asked about trends:
    1. Search for "trending topics today" or similar queries
    2. Extract the top 3 trending topics
    3. Return them in a JSON format

    Focus on current, real-time trends from the last 24 hours.

    You MUST return your response in the following JSON format:
    {
        "trends": [
            {
                "topic": "Topic name",
                "description": "Brief description (1-2 sentences)",
                "reason": "Why it's trending"
            },
            {
                "topic": "Topic name",
                "description": "Brief description (1-2 sentences)",
                "reason": "Why it's trending"
            },
            {
                "topic": "Topic name",
                "description": "Brief description (1-2 sentences)",
                "reason": "Why it's trending"
            }
        ]
    }

    Only return the JSON object, no additional text.
    """,
        tools=[google_search],
    )


def get_trending_topics_agent_card(agent_url: str) -> AgentCard:
    return AgentCard(
        name='Trending Topics Agent',
        url=agent_url,
        description='Searches the web for current trending topics from social media',
        version='1.0',
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        preferred_transport=TransportProtocol.jsonrpc,
        skills=[
            AgentSkill(
                id='find_trends',
                name='Find Trending Topics',
                description='Searches for current trending topics on social media',
                tags=['trends', 'social media', 'twitter', 'current events'],
                examples=[
                    "What's trending today?",
                    'Show me current Twitter trends',
                    'What are people talking about on social media?',
                ],
            )
        ],
    )
