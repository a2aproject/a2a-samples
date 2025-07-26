#!/usr/bin/env python3
"""
Azure AI Agents Diagnostic Script

This script helps diagnose common issues with Azure AI Agents setup.
"""

import os
import asyncio
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential


async def test_azure_connection():
    """Test Azure AI Agents connection and configuration."""
    print("🔍 Azure AI Agents Diagnostic Tool")
    print("=" * 50)
    
    # Check environment variables
    print("\n📊 Environment Variables Check:")
    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    model = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
    
    if not endpoint:
        print("❌ AZURE_AI_AGENT_ENDPOINT not set")
        return False
    else:
        print(f"✅ AZURE_AI_AGENT_ENDPOINT: {endpoint}")
    
    if not model:
        print("❌ AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME not set")
        return False
    else:
        print(f"✅ AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: {model}")
    
    # Test Azure authentication
    print("\n🔐 Azure Authentication Test:")
    try:
        credential = DefaultAzureCredential()
        print("✅ DefaultAzureCredential created successfully")
    except Exception as e:
        print(f"❌ Azure authentication failed: {e}")
        return False
    
    # Test Azure AI Agents client
    print("\n🤖 Azure AI Agents Client Test:")
    try:
        client = AgentsClient(
            endpoint=endpoint,
            credential=credential,
        )
        print("✅ AgentsClient created successfully")
    except Exception as e:
        print(f"❌ AgentsClient creation failed: {e}")
        return False
    
    # Test agent creation with simple instructions
    print("\n🎯 Agent Creation Test:")
    try:
        agent = client.create_agent(
            model=model,
            name="diagnostic-test-agent",
            instructions="You are a helpful assistant for testing purposes.",
        )
        print(f"✅ Agent created successfully with ID: {agent.id}")
        
        # Test thread creation
        print("\n💬 Thread Creation Test:")
        thread = client.threads.create()
        print(f"✅ Thread created successfully with ID: {thread.id}")
        
        # Test message creation
        print("\n📝 Message Creation Test:")
        message = client.messages.create(
            thread_id=thread.id,
            role="user",
            content="Hello, this is a test message."
        )
        print(f"✅ Message created successfully with ID: {message.id}")
        
        # Test run creation
        print("\n🏃 Run Creation Test:")
        run = client.runs.create(
            thread_id=thread.id,
            agent_id=agent.id
        )
        print(f"✅ Run created successfully with ID: {run.id}")
        print(f"Run status: {run.status}")
        
        # Wait for run completion (with timeout)
        print("\n⏳ Waiting for run completion...")
        max_wait = 30
        waited = 0
        while run.status in ["queued", "in_progress", "requires_action"] and waited < max_wait:
            await asyncio.sleep(1)
            waited += 1
            run = client.runs.get(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status} (waited {waited}s)")
        
        if run.status == "completed":
            print("✅ Run completed successfully!")
            
            # Get messages
            messages = client.messages.list(thread_id=thread.id)
            for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    response = msg.text_messages[-1].text.value
                    print(f"✅ Agent response: {response[:100]}...")
                    break
        elif run.status == "failed":
            print(f"❌ Run failed: {run.last_error}")
            return False
        else:
            print(f"⚠️  Run timed out with status: {run.status}")
        
        # Cleanup
        print("\n🧹 Cleanup:")
        client.delete_agent(agent.id)
        print("✅ Test agent deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation/testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'client' in locals():
                client.close()
                print("✅ Client connection closed")
        except:
            pass


async def main():
    """Run the diagnostic tests."""
    success = await test_azure_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Your Azure AI Agents setup is working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above and:")
        print("   1. Verify your Azure environment variables are correct")
        print("   2. Ensure you're authenticated with Azure (try 'az login')")
        print("   3. Check that your model deployment exists in Azure AI Studio")
        print("   4. Verify your Azure AI project endpoint is correct")


if __name__ == "__main__":
    asyncio.run(main())
