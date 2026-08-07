"""Simple client for testing the Hello World Azure AI Foundry Agent."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .hello_agent import HelloWorldAgent


async def interactive_client() -> None:
    """Interactive client for chatting with the Hello World agent."""
    logging.basicConfig(level=logging.WARNING)  # Reduce noise in interactive mode
    
    print("🤖 Hello World Azure AI Foundry Agent - Interactive Client")
    print("=" * 60)
    print("Type 'quit', 'exit', or press Ctrl+C to end the conversation.")
    print()
    
    agent = HelloWorldAgent()
    
    try:
        await agent.create_agent()
        thread = await agent.create_thread()
        
        print("✅ Agent initialized successfully!")
        print("🔄 You can now start chatting with the agent.")
        print()
        
        while True:
            try:
                user_input = input("👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Agent is thinking...")
                responses = await agent.run_conversation(thread.id, user_input)
                
                for response in responses:
                    print(f"🤖 Agent: {response}")
                print()
                
            except KeyboardInterrupt:
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("\n🧹 Cleaning up...")
        await agent.cleanup_agent()
        print("👋 Goodbye!")


async def batch_client(messages: list[str]) -> None:
    """Batch client for testing multiple messages."""
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 Hello World Azure AI Foundry Agent - Batch Client")
    print("=" * 60)
    
    agent = HelloWorldAgent()
    
    try:
        await agent.create_agent()
        thread = await agent.create_thread()
        
        for i, message in enumerate(messages, 1):
            print(f"\n📝 Message {i}/{len(messages)}: {message}")
            responses = await agent.run_conversation(thread.id, message)
            
            for response in responses:
                print(f"🤖 Response: {response}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await agent.cleanup_agent()


async def main() -> None:
    """Main function to choose between interactive and batch mode."""
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # Batch mode with predefined messages
        test_messages = [
            "Hello there!",
            "What can you help me with?",
            "Tell me something interesting",
            "How are you today?",
            "Thank you for the chat!"
        ]
        await batch_client(test_messages)
    else:
        # Interactive mode
        await interactive_client()


if __name__ == "__main__":
    asyncio.run(main())
