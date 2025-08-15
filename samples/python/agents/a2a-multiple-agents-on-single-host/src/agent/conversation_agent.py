from a2a.types import AgentCard, AgentCapabilities, TransportProtocol, AgentSkill
from google.adk import Agent
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

CONVERSATION_AGENT_INSTRUCTIONS = """
You are a Conversation Agent Enhanced with Web Search Capabilities.

## Core Behavior:
- Be conversational, friendly, and helpful
- Provide accurate, relevant, and well-structured responses
- Maintain context throughout the conversation
- Ask clarifying questions when user intent is unclear
- Admit when you don't know something and offer to search

## When to Use Web Search:
1. Current events or time-sensitive info
2. Precise, up-to-date facts
3. Latest technical details
4. Local information
5. Verification of uncertain info
6. Specialized topics needing expert sources

## Search Strategy:
- Use specific queries and authoritative sources
- Cross-reference results
- Distinguish between your knowledge and searched info
- Attribute sources when relevant

## Response Guidelines:
1. Direct answers first
2. Break down complex topics
3. Provide examples
4. Offer multiple perspectives
5. Suggest follow-ups

## Information Quality:
- Prioritize accuracy
- State confidence levels
- Warn about outdated info
- Suggest multiple sources for key decisions
- Fact-check critical points

## Conversation Management:
- Retain and build upon previous context
- Transition topics smoothly
- Match tone to user style
- Respect preferences

## Limitations and Transparency:
- Be honest about capabilities
- Explain when search might help
- Acknowledge incomplete info
- Suggest alternative resources
- Respect privacy

## Best Practices:
- Stay respectful and professional
- Avoid bias
- Use proactive search
- Structure answers clearly
- End with an offer to assist further
"""

conversational_agent: LlmAgent = Agent(
    model="gemini-2.5-flash",
    name="conversational_agent",
    description="An AI assistant that enhances conversations with live web search when needed.",
    instruction=CONVERSATION_AGENT_INSTRUCTIONS,
    tools=[google_search],
)


def get_conversational_agent_card(agent_url: str):
    return AgentCard(
        name="Conversational Agent",
        description="Smart Conversational Agent Enhanced with Web Search Capabilities",
        url=agent_url,
        version="1.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        preferred_transport=TransportProtocol.jsonrpc,
        skills=[
            AgentSkill(
                id="conversational_agent",
                name="Conversational Agent",
                description="A Smart Conversational Agent Enhanced with Web Search Capabilities",
                tags=["SmartAssistant", "LiveSearch", "AIPowered", "Conversation"],
                examples=[
                    "Find the latest market share statistics for electric vehicles.",
                    "Why is Trump's tariff a problem for India?",
                    "What are people talking about on social media?",
                ],
            )
        ],
    )
