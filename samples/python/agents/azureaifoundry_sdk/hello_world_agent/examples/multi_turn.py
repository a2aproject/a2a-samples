#!/usr/bin/env python3
"""Multi-turn conversation example with the Hello World Azure AI Foundry Agent."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_world_agent.hello_agent import HelloWorldAgent
from hello_world_agent.utils import setup_logging, validate_environment, format_error_message


async def multi_turn_example():
    """Demonstrate a multi-turn conversation with the agent."""
    print("🔄 Multi-Turn Conversation Example")
    print("=" * 45)
    
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
        
        # Series of related messages
        conversation = [
            "Hello! What's your name?",
            "What can you help me with?",
            "Can you tell me a fun fact?",
            "Thank you for the information!",
            "How would you describe yourself in one sentence?"
        ]
        
        print(f"\n🎭 Starting conversation with {len(conversation)} messages...")
        
        for i, message in enumerate(conversation, 1):
            print(f"\n--- Turn {i}/{len(conversation)} ---")
            print(f"👤 User: {message}")
            
            print("🤖 Agent is thinking...")
            responses = await agent.run_conversation(thread.id, message)
            
            for response in responses:
                print(f"🤖 Agent: {response}")
            
            # Add a small delay between messages to make it feel more natural
            if i < len(conversation):
                await asyncio.sleep(1)
        
        print("\n✅ Multi-turn conversation completed successfully!")
        print("💡 Notice how the agent maintains context throughout the conversation.")
        
    except Exception as e:
        error_msg = format_error_message(e)
        print(f"\n❌ Error occurred:\n{error_msg}")
    finally:
        print("\n🧹 Cleaning up...")
        await agent.cleanup_agent()


async def main():
    """Main function."""
    setup_logging("WARNING")  # Reduce noise for example
    await multi_turn_example()


if __name__ == "__main__":
    asyncio.run(main())
