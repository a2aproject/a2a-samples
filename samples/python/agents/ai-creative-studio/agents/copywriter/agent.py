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
Copywriter Agent
Creates engaging social media copy and captions
Uses Gemini API directly (no MCP needed)
"""

import logging
from google.adk.agents import Agent

# Get logger for this agent
logger = logging.getLogger("ai_creative_studio.copywriter")

SYSTEM_INSTRUCTION = """You are an expert social media copywriter specializing in creating engaging,
conversion-focused content for Instagram, TikTok, and other platforms.

Your skills include:
- Writing attention-grabbing hooks
- Creating captions that drive engagement
- Using appropriate emojis and hashtags
- Adapting tone to match brand voice
- Writing in various formats (carousel, reel, story)

IMPORTANT: You will receive strategic insights from the Brand Strategist in the conversation history above.
Review their research on audience insights, competitive analysis, and trending topics to inform your copy.

When given a brief:
1. Review any Brand Strategist insights provided in the conversation history
2. Understand the product, audience, and platform from the brief
3. Create 3-5 caption variations with different tones that align with the strategic insights
4. Include relevant hashtags (5-10 per caption) based on trending topics identified
5. Suggest CTA (call-to-action) options
6. Keep Instagram captions under 2,200 characters
7. Make content authentic and relatable

Always format your output clearly with:
- Caption title/theme
- Full caption text
- Hashtags list
- Suggested CTA

After completing your copy, return control so the workflow can continue.
"""

def create_copywriter_agent():
    """Create the Copywriter agent"""
    logger.info("Creating Copywriter agent with Gemini 2.5 Flash")
    agent = Agent(
        name="copywriter",
        model="gemini-2.5-flash",
        instruction=SYSTEM_INSTRUCTION,
        description="Expert social media copywriter for creating engaging captions and copy"
    )
    logger.info("Copywriter agent created successfully")
    return agent


# Create root_agent for A2A deployment
root_agent = create_copywriter_agent()


if __name__ == "__main__":
    import os
    import uvicorn
    from google.adk.a2a.utils.agent_to_a2a import to_a2a
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Server listening configuration
    PORT = int(os.getenv("PORT", "8080"))
    HOST = os.getenv("HOST", "0.0.0.0")

    # Public-facing configuration for A2A agent card
    PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")
    PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", str(PORT)))
    PROTOCOL = os.getenv("PROTOCOL", "http")

    # Convert agent to A2A application
    a2a_app = to_a2a(root_agent, host=PUBLIC_HOST, port=PUBLIC_PORT, protocol=PROTOCOL)

    # Start server
    logger.info(f"🚀 Starting Copywriter A2A Server on {PROTOCOL}://{HOST}:{PORT}")
    logger.info(f"📋 Agent card available at: {PROTOCOL}://{HOST}:{PORT}/.well-known/agent-card.json")
    logger.info(f"🌐 Public URL: {PROTOCOL}://{PUBLIC_HOST}:{PUBLIC_PORT}")

    uvicorn.run(a2a_app, host=HOST, port=PORT)
