"""
Test Project Manager agent locally with Notion MCP
"""
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(dotenv_path="../../.env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import the agent after loading .env
from agent import create_project_manager_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def test_pm_with_notion():
    """Test Project Manager agent with Notion integration"""

    # Check environment variables
    notion_key = os.getenv('NOTION_API_KEY')
    notion_db = os.getenv('NOTION_DATABASE_ID')

    print("\n" + "="*70)
    print("🧪 Testing Project Manager Agent Locally")
    print("="*70)
    print(f"NOTION_API_KEY: {notion_key[:20] if notion_key else 'NOT SET'}...")
    print(f"NOTION_DATABASE_ID: {notion_db}")
    print("="*70 + "\n")

    if not notion_key or not notion_db:
        print("❌ ERROR: Notion credentials not found in .env")
        print("Please ensure .env file contains:")
        print("  - NOTION_API_KEY=your_api_key")
        print("  - NOTION_DATABASE_ID=your_database_id")
        sys.exit(1)

    # Create the agent
    print("📦 Creating Project Manager agent with Notion MCP...")
    agent = create_project_manager_agent()
    print("✅ Agent created successfully\n")

    # Create runner
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test_pm",
        agent=agent,
        session_service=session_service
    )

    # Test brief
    brief = """Create a project timeline for:
    - Product: EcoBrew Coffee Launch
    - Timeline: 2 weeks
    - Budget: $3,000
    - Deliverables: 3 Instagram posts, 1 landing page

    Please create the timeline and save it to Notion.
    """

    print("📝 Test Query:")
    print(brief)
    print("\n" + "="*70)
    print("🚀 Running agent...")
    print("="*70 + "\n")

    session_id = "test_local_pm"
    user_id = "test_user"

    try:
        # Create session
        await session_service.create_session(
            app_name="test_pm",
            user_id=user_id,
            session_id=session_id
        )

        # Run agent
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text=brief)])
        ):
            print("EVENT TYPE:", type(event).__name__)
            print("EVENT RAW:", event)
            print("-" * 50)
            if getattr(event, 'text', None):
                print(event.text, end='', flush=True)
            

    finally:
        await runner.close()

    print("\n\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70)

if __name__ == "__main__":
    try:
        asyncio.run(test_pm_with_notion())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
