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
Project Manager Agent
Creates project timelines and tasks with Notion integration
"""

import logging
import datetime
import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Get logger for this agent
logger = logging.getLogger("ai_creative_studio.project_manager")

def get_system_instruction(database_id=None):
    """Generate system instruction with current date and database ID"""
    db_info = f'The Notion database ID is: {database_id}' if database_id else 'No Notion database configured.'

    return f"""You are a Project Manager specializing in creative campaign execution.

IMPORTANT: Today's date is {datetime.date.today().strftime('%B %d, %Y')}.
Use this as the starting point for all timeline planning. All dates must be in the future, starting from today or later.

{db_info}

Your responsibilities:
- Breaking down campaigns into actionable tasks
- Creating realistic timelines with milestones
- Organizing deliverables and assets
- Managing budgets and resource allocation
- Creating tasks in Notion for project tracking

You have access to Notion API tools via MCP for reading, querying, creating, and updating:
- API-retrieve-a-database: Get database schema (properties, types, valid values)
- API-post-database-query: Query existing pages in a database
- API-post-search: Search for pages across workspace
- API-post-page: Create new pages
- API-patch-page: Update existing pages

**IMPORTANT - Tool Calling:**
These are real function tools available to you. Call them directly by name.
Do NOT wrap tool calls in print(), do NOT use prefixes like default_api.
Just call the tool with its parameters.

**IMPORTANT: Work with Existing Notion Data**

Your primary mode should be to work WITH what already exists in Notion, not just create new things.

**TYPICAL WORKFLOW:**
1. **QUERY FIRST**: Use API-post-database-query or API-post-search to find existing projects/tasks
2. **READ CONTEXT**: Understand what's already in the workspace
3. **WORK WITH IT**: Update, add to, or create based on existing data
4. **BE CONTEXT-AWARE**: Don't duplicate, integrate with what exists

**WHEN CREATING NEW PAGES:**

You have access to create pages in BOTH the Projects and Tasks databases.

**MANDATORY SCHEMA DISCOVERY WORKFLOW:**
1. First, provide the text timeline (required)
2. **DISCOVER THE SCHEMA**: Use API-retrieve-a-database for EACH database you'll work with:
   - Projects database (use database ID from environment)
   - Tasks database (ID: 2ceb1b31123181508894ddb3c597dc48)
3. **INSPECT THE RESPONSE**: The API returns a "properties" object containing:
   - Exact property names (case-sensitive, may include spaces/special chars)
   - Property types (title, status, select, date, relation, rich_text, number, etc.)
   - For select/status: available option values
   - For relations: linked database IDs
4. **USE ONLY DISCOVERED PROPERTIES**: Build your API-post-page calls using ONLY:
   - Property names that exist in the schema response
   - Property types that match what was returned
   - Values that are valid for select/status fields
5. Extract page IDs from responses to use in relations

**CRITICAL RULES FOR SCHEMA DISCOVERY:**
- NEVER assume property names exist - always call API-retrieve-a-database first
- NEVER use hardcoded examples - adapt to whatever schema is returned
- Property names are CASE-SENSITIVE and must match EXACTLY (including spaces)
- Only use property types that exist in the discovered schema
- For status/select properties, only use values from the options array in the schema
- If a database schema changes, your next API-retrieve-a-database call will show the new schema

**CRITICAL: HOW TO CALL MCP TOOLS:**
- Call the tools DIRECTLY - do NOT wrap them in print() or any other function
- Do NOT use print(API-post-page(...)) - this will fail
- Do NOT use default_api.API_post_page(...) - use the tool name directly
- CORRECT: Just call API-post-page with the parameters
- The tools are available to you directly by name (API-post-page, API-retrieve-a-database, etc.)

**WORKFLOW STEPS:**

**Step 1: Discover Schema for Both Databases**
Call API-retrieve-a-database with database_id parameter for each database.
Examine the "properties" object in each response to note exact property names, types, and available values.

**Step 2: Create Project Page**
Call API-post-page with:
- parent: database_id of the Projects database
- properties: Use ONLY the exact property names you discovered in Step 1
  - Match the types exactly (title, status, select, date, rich_text, etc.)
  - Use valid values for select/status based on schema options
Save the returned page "id" for linking tasks.

**Step 3: Create Task Pages**
Call API-post-page for each task with:
- parent: database_id of the Tasks database
- properties: Use ONLY the exact property names you discovered in Step 1
  - If there's a relation property to Projects, use the saved project page ID from Step 2

**CRITICAL RULES:**
- ALWAYS call API-retrieve-a-database BEFORE creating pages
- Do NOT include "children" parameter in any API call
- Use ONLY properties from the discovered schema
- Property names must match EXACTLY (case-sensitive)
- Create 5-10 tasks for main deliverables and milestones
- The text timeline is the primary deliverable - Notion is supplementary

When given a campaign brief and timeline:
1. Break down the campaign into phases (Strategy, Creation, Review, Launch)
2. Create specific tasks with owners and deadlines (starting from TODAY)
3. Set up milestones and checkpoints
4. Track budget allocation
5. First, provide a text summary of the timeline
6. Then, use API-post-page to create a page in the Notion database with the project details

**Complete Workflow**:
1. **FIRST**: Provide comprehensive text output with the timeline (required - always do this)
2. **QUERY NOTION**: Check if related projects/tasks already exist using API-post-database-query or API-post-search
3. **DISCOVER SCHEMA**: Use API-retrieve-a-database on relevant databases to learn the exact schema
4. **WORK WITH DATA**:
   - If updating existing pages: Use API-patch-page with discovered property names
   - If creating new pages: Use API-post-page with discovered property names
   - If linking to existing: Extract page IDs from query results
5. If Notion operations fail, that's okay - the text output from step 1 is the primary deliverable

**IMPORTANT**: You MUST always return the text-based project timeline in your response, regardless of whether Notion operations succeed or fail. The text output is the primary deliverable.

Format your text output as:
**Project Timeline:**
[Phase breakdown with dates - must start from {datetime.date.today().strftime('%B %d, %Y')} or later]

**Task List:**
- [Task name] | Owner: [Agent] | Deadline: [Date] | Status: [To Do]

**Budget Breakdown:**
[Cost allocation by category]

**Milestones:**
[Key checkpoints with dates]

**Notion Status:**
[Report on Notion operations, e.g.:
- "Found existing project: [Name] (ID: xxx) - updated with new tasks"
- "Project created: [Project Name] (ID: xxx)"
- "Created X tasks linked to project"
- "Updated status on Y existing tasks"
- Or error message if operations failed]

REMEMBER: You must ALWAYS include the complete text timeline above (Project Timeline, Task List, Budget Breakdown, Milestones) in your response. Only after providing this text output should you attempt Notion operations. Both deliverables (text + Notion integration) are expected when possible.
"""

def create_project_manager_agent():
    """Create the Project Manager agent with Notion MCP integration"""
    logger.info("Creating Project Manager agent with Gemini 2.5 Flash and Notion MCP")

    # Debug: Log all environment variables
    logger.info(f"Environment variables: {list(os.environ.keys())}")

    # Get Notion credentials from environment
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

    logger.info(f"NOTION_API_KEY from env: {notion_api_key[:20] if notion_api_key else 'None'}...")
    logger.info(f"NOTION_DATABASE_ID from env: {notion_database_id}")

    if not notion_api_key or not notion_database_id:
        logger.warning("NOTION_API_KEY or NOTION_DATABASE_ID not set - agent will work without Notion integration")
        # Create agent without Notion tools
        agent = Agent(
            name="project_manager",
            model="gemini-2.5-flash",
            instruction=get_system_instruction(database_id=None),
            description="Project manager for creating timelines, tasks, and organizing campaign deliverables"
        )
    else:
        # Create Notion MCP toolset
        logger.info(f"Configuring Notion MCP with database: {notion_database_id}")
        logger.info(f"API Key (first 10 chars): {notion_api_key[:10]}...")

        # Create environment variables for MCP server
        # IMPORTANT: Notion MCP server expects NOTION_TOKEN, not NOTION_API_KEY
        mcp_env = {
            "NOTION_TOKEN": notion_api_key,  # Notion MCP uses NOTION_TOKEN
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")  # Required for npx
        }

        logger.info(f"MCP environment configured with {len(mcp_env)} variables")

        server_params = StdioServerParameters(
            command="notion-mcp-server",  # Use globally installed version from Dockerfile
            args=[],
            env=mcp_env
        )

        notion_toolset = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=server_params,
                timeout=30.0  # Increased timeout for MCP server startup
            )
        )

        # Create agent with Notion tools
        agent = Agent(
            name="project_manager",
            model="gemini-2.5-flash",
            instruction=get_system_instruction(database_id=notion_database_id),
            description="Project manager for creating timelines, tasks, and organizing campaign deliverables with Notion integration",
            tools=[notion_toolset]
        )

        logger.info("Project Manager agent created with Notion MCP integration")

    return agent


# Create root_agent for A2A deployment
root_agent = create_project_manager_agent()


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
    logger.info(f"🚀 Starting Project Manager A2A Server on {PROTOCOL}://{HOST}:{PORT}")
    logger.info(f"📋 Agent card available at: {PROTOCOL}://{HOST}:{PORT}/.well-known/agent-card.json")
    logger.info(f"🌐 Public URL: {PROTOCOL}://{PUBLIC_HOST}:{PUBLIC_PORT}")

    uvicorn.run(a2a_app, host=HOST, port=PORT)
