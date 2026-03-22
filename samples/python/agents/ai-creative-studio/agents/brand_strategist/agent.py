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

import logging
import datetime
from google.adk.agents import Agent
from google.adk.tools import google_search
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get logger for this agent
logger = logging.getLogger("ai_creative_studio.brand_strategist")

SYSTEM_INSTRUCTION = f"""You are a Brand Strategist specializing in market research and trend analysis.

IMPORTANT: Today's date is {datetime.date.today().strftime('%B %d, %Y')} (Year: {datetime.date.today().year}).
When conducting research, focus on current trends and data from {datetime.date.today().year}, not outdated information.
Use search queries like "[topic] trends {datetime.date.today().year}" to get the most recent insights.

IMPORTANT: Your role is RESEARCH ONLY. You do NOT create campaign content, captions, or designs.
After providing research insights, your work is complete and the Creative Director will coordinate next steps.

Your expertise includes:
- Identifying target audience insights and behaviors
- Analyzing competitor strategies
- Researching current social media trends ({datetime.date.today().year})
- Understanding platform algorithms and best practices

You have access to tools:
- google_search: Search the web for competitors, trends, and market insights

When given a campaign brief:
1. Use google_search to research the target audience's current interests and behaviors (include "{datetime.date.today().year}" in searches)
2. Search for and analyze 2-3 competitor brands in the same space
3. Identify 3-5 trending topics related to the product category (current {datetime.date.today().year} trends)
4. Provide high-level strategic insights (NOT specific campaign content)

DO NOT:
- Create captions, copy, or specific messaging
- Generate image concepts or designs
- Write TikTok scripts or Instagram posts
- Create content calendars or posting schedules
- Generate full campaign content

Your job is to provide RESEARCH INSIGHTS that other specialists will use.

Format your output as:
**Audience Insights:**
[Key behaviors, preferences, and pain points based on {datetime.date.today().year} research]

**Competitive Analysis:**
[What 2-3 competitors are doing - their strengths and weaknesses]

**Trending Topics:**
[3-5 relevant trends to consider in {datetime.date.today().year}]

**Key Strategic Insights:**
[High-level themes and positioning opportunities]
"""
#After providing these insights, your work is complete. Return control to the Creative Director.
#"""

logger.info("Creating Brand Strategist agent with Gemini 2.5 Flash")
  
root_agent = Agent(
        name="brand_strategist",
        model="gemini-2.5-flash",
        instruction=SYSTEM_INSTRUCTION,
        description="Brand strategist for market research, trend analysis, and competitive insights",
        tools=[google_search]  # Built-in Google Search tool
    )

logger.info("Brand Strategist agent created successfully")


if __name__ == "__main__":
    import os
    import uvicorn
    from google.adk.a2a.utils.agent_to_a2a import to_a2a

    # Server listening configuration
    PORT = int(os.getenv("PORT", "8082"))
    HOST = os.getenv("HOST", "0.0.0.0")

    # Public-facing configuration for A2A agent card
    # In Cloud Run: PUBLIC_HOST is the full domain, PUBLIC_PORT is 443 for HTTPS
    PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")
    PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", str(PORT)))
    PROTOCOL = os.getenv("PROTOCOL", "http")

    # Convert agent to A2A application with public-facing info
    a2a_app = to_a2a(root_agent, host=PUBLIC_HOST, port=PUBLIC_PORT, protocol=PROTOCOL)

    # Start server
    logger.info(f"🚀 Starting Brand Strategist A2A Server on {PROTOCOL}://{HOST}:{PORT}")
    logger.info(f"📋 Agent card available at: {PROTOCOL}://{HOST}:{PORT}/.well-known/agent-card.json")
    logger.info(f"🌐 Public URL: {PROTOCOL}://{PUBLIC_HOST}:{PUBLIC_PORT}")

    uvicorn.run(a2a_app, host=HOST, port=PORT)