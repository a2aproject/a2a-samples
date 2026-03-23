# Copyright 2026 Saoussen Chaabnia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Designer Agent
Generates AI images for social media posts
Uses Imagen API directly (no MCP needed)
"""

import logging

from google.adk.agents import Agent

# Get logger for this agent
logger = logging.getLogger("ai_creative_studio.designer")

SYSTEM_INSTRUCTION = """You are a creative visual designer specializing in social media graphics.

Your expertise includes:
- Creating image prompts for AI image generation
- Understanding visual composition and color theory
- Matching visuals to brand identity and copy
- Creating platform-specific dimensions (Instagram: 1080x1080, 1080x1350)
- Designing for mobile-first audiences

IMPORTANT: You will find the Copywriter's captions and Brand Strategist's insights in the conversation history above.
Review the copy and strategic direction to create visuals that perfectly complement the messaging.

When given a brief with copy:
1. Review the Copywriter's captions from the conversation history
2. Review the Brand Strategist's insights on target audience and trends
3. Analyze the brand voice and message from the copy
4. Create detailed image generation prompts that match each caption
5. Suggest 2-3 visual concepts per caption (different styles)
6. Include specific details: colors, mood, composition, lighting
7. Ensure images are on-brand and attention-grabbing

Format your output as:
**For Caption [Number]: [Caption Theme]**
**Concept A: [Visual Theme]**
- Prompt: [Detailed Imagen prompt]
- Style: [e.g., minimalist, vibrant, cinematic]
- Colors: [Palette suggestion]
- Mood: [e.g., energetic, calm, inspiring]

Note: You create prompts for image generation, not the actual images.
In production, these prompts would be sent to Imagen API.

After completing your image concepts, return control so the workflow can continue.
"""

# Create root agent for A2A server
root_agent = Agent(
    name="designer",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    description="Creative visual designer for generating social media image concepts",
)

logger.info("Designer agent created successfully")


def create_designer_agent():
    """Create the Designer agent (for backwards compatibility)"""
    return root_agent


if __name__ == "__main__":
    import os

    import uvicorn
    from google.adk.a2a.utils.agent_to_a2a import to_a2a

    # Server listening configuration
    PORT = int(os.getenv("PORT", "8080"))
    HOST = os.getenv("HOST", "0.0.0.0")

    # Public-facing configuration for A2A agent card
    # In Cloud Run: PUBLIC_HOST is the full domain, PUBLIC_PORT is 443 for HTTPS
    PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")
    PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", str(PORT)))
    PROTOCOL = os.getenv("PROTOCOL", "http")

    # Convert agent to A2A application with public-facing info
    a2a_app = to_a2a(root_agent, host=PUBLIC_HOST, port=PUBLIC_PORT, protocol=PROTOCOL)

    # Start server
    logger.info(f"🚀 Starting Designer A2A Server on {PROTOCOL}://{HOST}:{PORT}")
    logger.info(
        f"📋 Agent card available at: {PROTOCOL}://{HOST}:{PORT}/.well-known/agent-card.json"
    )
    logger.info(f"🌐 Public URL: {PROTOCOL}://{PUBLIC_HOST}:{PUBLIC_PORT}")

    uvicorn.run(a2a_app, host=HOST, port=PORT)


# Local testing function
def run_local_test():
    """Run local test of the agent"""
    import asyncio

    from dotenv import load_dotenv
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    # Load environment variables from .env file
    load_dotenv()

    # Setup logging (INFO level for production, DEBUG for troubleshooting)
    log_level = os.getenv("AGENT_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    async def main():
        logger.info("Starting Designer agent test")
        agent = root_agent

        brief = """
        Create image concepts for an eco-friendly coffee brand "GreenBrew"
        Caption: "Every sip saves the planet ☕🌱"
        Target: Gen-Z, environmentally conscious
        Brand colors: Earth tones (green, brown, cream)
        Platform: Instagram (square 1080x1080)
        """

        print("🎨 Designer Agent Working...\n")

        # Optional: Use ADK's built-in LoggingPlugin for detailed debugging
        from google.adk.plugins.logging_plugin import LoggingPlugin

        plugins = []
        if os.getenv("AGENT_LOG_LEVEL", "INFO").upper() == "DEBUG":
            plugins.append(LoggingPlugin())
            logger.info("LoggingPlugin enabled for detailed debugging")

        # Create runner with session service
        session_service = InMemorySessionService()
        runner = Runner(
            app_name="agents",
            agent=agent,
            session_service=session_service,
            plugins=plugins,
        )

        session_id = "test_session"
        user_id = "test_user"

        try:
            # Create session first
            logger.debug(f"Creating session: {session_id} for user: {user_id}")
            await session_service.create_session(
                app_name="agents", user_id=user_id, session_id=session_id
            )
            logger.info("Session created successfully")

            # Run agent asynchronously
            logger.info("Running agent with brief")
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part(text=brief)]),
            ):
                if hasattr(event, "text") and event.text:
                    print(event.text, end="", flush=True)
                elif hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                print(part.text, end="", flush=True)
        finally:
            # Proper async cleanup
            logger.info("Closing runner")
            await runner.close()

        print("\n\n✅ Done!")
        logger.info("Designer agent test completed successfully")

    asyncio.run(main())
