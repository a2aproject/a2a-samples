import os
from a2a.types import AgentCard, AgentProvider, SecurityScheme
from dotenv import load_dotenv

load_dotenv()

agent_card = AgentCard(
    name="Real Estate Agent",
    description="An agent to find real estate properties.",
    url=os.environ.get("AGENT_PUBLIC_URL", "http://localhost:3001/"),
    provider=AgentProvider(
        organization="Amine Remache",
        url="https://github.com/amineremache/dafty-mcp",
    ),
    version="0.1.2",
    capabilities={
        "streaming": True,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    securitySchemes={
        "bearer_auth": SecurityScheme(
            type="http",
            scheme="bearer",
        )
    },
    security=[{"bearer_auth": []}],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    skills=[
        {
            "id": "search_rentals",
            "name": "Search Rentals",
            "description": "Search for rental properties.",
            "tags": ["real estate", "rentals"],
            "examples": [
                "Find a 2-bed apartment in Dublin under €2000.",
                "Show me houses for rent in Cork.",
            ],
            "inputModes": ["text/plain"],
            "outputModes": ["text/plain"],
        }
    ],
    supportsAuthenticatedExtendedCard=False,
)