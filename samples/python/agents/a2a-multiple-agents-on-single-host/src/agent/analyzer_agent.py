from a2a.types import AgentCard, AgentCapabilities, TransportProtocol, AgentSkill
from google.adk import Agent
from google.adk.tools import google_search

analyzer_agent = Agent(
    model='gemini-2.5-flash',
    name='trend_analyzer_agent',
    instruction="""
    You are a data analyst specializing in trend analysis. When given a trending topic,
    perform deep research to find quantitative data and insights.

    For each trend you analyze:
    1. Search for statistics, numbers, and metrics related to the trend
    2. Look for:
       - Engagement metrics (views, shares, mentions)
       - Growth rates and timeline
       - Geographic distribution
       - Related hashtags or keywords
    3. Provide concrete numbers and data points

    Keep it somehow concise

    Always prioritize quantitative information over qualitative descriptions.
    """,
    tools=[google_search],
)


def get_analyzer_agent_card(agent_url):
    return AgentCard(
        name='Trend Analyzer Agent',
        url=agent_url,
        description='Performs deep analysis of trends with quantitative data',
        version='1.0',
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        preferred_transport=TransportProtocol.jsonrpc,
        skills=[
            AgentSkill(
                id='analyze_trend',
                name='Analyze Trend',
                description='Provides quantitative analysis of a specific trend',
                tags=['analysis', 'data', 'metrics', 'statistics'],
                examples=[
                    'Analyze the #ClimateChange trend',
                    'Get metrics for the Taylor Swift trend',
                    'Provide data analysis for AI adoption trend',
                ],
            )
        ],
    )
