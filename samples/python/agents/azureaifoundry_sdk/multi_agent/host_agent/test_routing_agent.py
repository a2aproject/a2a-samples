import os
import asyncio
from routing_agent import RoutingAgent


async def test_routing_agent():
    """Test the RoutingAgent initialization and basic functionality."""
    print("🧪 Testing RoutingAgent initialization...")
    
    # First, run Azure diagnostics
    print("\n🔍 Running Azure AI diagnostics first...")
    try:
        from diagnose_azure import test_azure_connection
        azure_works = await test_azure_connection()
        if not azure_works:
            print("⚠️  Azure AI connection issues detected. Continuing with routing agent test...")
    except ImportError:
        print("⚠️  Diagnostic script not available. Continuing with routing agent test...")
    
    try:
        # Create routing agent
        print("\n🤖 Creating RoutingAgent...")
        routing_agent = await RoutingAgent.create(
            remote_agent_addresses=[
                os.getenv('TOOL_AGENT_URL', 'http://localhost:10002'),
                os.getenv('PLAYWRIGHT_AGENT_URL', 'http://localhost:10001'),
            ]
        )
        print("✅ RoutingAgent created successfully")
        
        # Check attributes
        print("\n📊 Checking RoutingAgent attributes:")
        print(f"  - azure_agent: {hasattr(routing_agent, 'azure_agent')}")
        print(f"  - current_thread: {hasattr(routing_agent, 'current_thread')}")
        print(f"  - agents_client: {hasattr(routing_agent, 'agents_client')}")
        print(f"  - context: {hasattr(routing_agent, 'context')}")
        
        # Try to create Azure AI agent
        print("\n🤖 Attempting to create Azure AI agent...")
        try:
            azure_agent = routing_agent.create_agent()
            print(f"✅ Azure AI agent created with ID: {azure_agent.id}")
            
            # Test multiple message processing calls to verify HTTP transport works
            print("\n💬 Testing message processing with simple messages...")
            
            # First message - simple greeting
            print("Testing message 1...")
            response1 = await routing_agent.process_user_message("Hello")
            print(f"✅ First response: {response1[:100]}...")
            
            # Second message - this would fail with HTTP transport error if not fixed
            print("Testing message 2...")
            response2 = await routing_agent.process_user_message("How are you?")
            print(f"✅ Second response: {response2[:100]}...")
            
            # Third message
            print("Testing message 3...")
            response3 = await routing_agent.process_user_message("Thank you")
            print(f"✅ Third response: {response3[:100]}...")
            
            print("✅ All message processing calls succeeded - HTTP transport issue resolved!")
            
        except Exception as agent_error:
            print(f"⚠️  Azure AI agent creation/testing failed: {agent_error}")
            print("This might be due to:")
            print("  - Incorrect model deployment name")
            print("  - Azure authentication issues")
            print("  - Azure AI service configuration problems")
            print("\nRun 'python diagnose_azure.py' for detailed diagnostics")
        
        # Test cleanup
        print("\n🧹 Testing cleanup...")
        routing_agent.cleanup()
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_routing_agent())
