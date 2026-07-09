#!/usr/bin/env python3
"""Simple chat example with the Hello World Azure AI Foundry Agent."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_world_agent.hello_agent import HelloWorldAgent
from hello_world_agent.utils import setup_logging, validate_environment, format_error_message


async def simple_chat_example():
    """Demonstrate a simple chat interaction with the agent."""
    print("🚀 Simple Chat Example")
    print("=" * 40)
    
    # Validate environment
    env_check = validate_environment()
    if not env_check["valid"]:
        print("❌ Environment validation failed:")
        for var in env_check["missing_vars"]:
            print(f"   Missing: {var}")
        return
    
    agent = HelloWorldAgent()
    
    try:
        print("🔧 Creating agent...")
        await agent.create_agent()
        
        print("💬 Creating conversation thread...")
        thread = await agent.create_thread()
        
        # Simple interaction
        message = "Hello! Can you introduce yourself?"
        print(f"\n👤 User: {message}")
        
        print("🤖 Agent is processing...")
        responses = await agent.run_conversation(thread.id, message)
        
        for response in responses:
            print(f"🤖 Agent: {response}")
        
        print("\n✅ Simple chat example completed successfully!")
        
    except Exception as e:
        error_msg = format_error_message(e)
        print(f"\n❌ Error occurred:\n{error_msg}")
    finally:
        print("\n🧹 Cleaning up...")
        await agent.cleanup_agent()


async def main():
    """Main function."""
    setup_logging("WARNING")  # Reduce noise for example
    await simple_chat_example()


if __name__ == "__main__":
    asyncio.run(main())
