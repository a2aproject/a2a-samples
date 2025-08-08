"""
Test client for the iframe demo agent to verify iframe functionality works.
"""

import asyncio
import json

import httpx
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
)


async def test_iframe_agent():
    """Test the iframe demo agent functionality."""
    print("🧪 Testing Iframe Demo Agent...")
    
    # Test different iframe requests
    test_cases = [
        "show me a chart",
        "display a dashboard", 
        "show me a form",
        "embed https://example.com",
        "hello"  # Default capabilities message
    ]
    
    for i, test_message in enumerate(test_cases, 1):
        print(f"\n📤 Test {i}: '{test_message}'")
        
        # Create test message
        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=test_message))],
            message_id=f"test-{i}",
            context_id="test-context"
        )
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Send message to agent
                response = await client.post(
                    "http://localhost:10002/a2a/tasks/send",
                    json=message.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print("✅ Agent responded successfully")
                    
                    # Check if response contains iframe data
                    response_data = response.json()
                    print(f"📨 Response: {json.dumps(response_data, indent=2)[:200]}...")
                    
                    # Look for iframe indicators in the response
                    response_str = json.dumps(response_data)
                    if 'src' in response_str and any(word in test_message.lower() for word in ['chart', 'dashboard', 'form', 'embed']):
                        print("🎯 ✅ IFRAME DETECTED: Response contains iframe configuration!")
                    elif 'embed' in response_str or 'iframe' in response_str.lower():
                        print("🎯 ✅ IFRAME DETECTED: Response mentions iframe functionality!")
                    else:
                        print("📄 Standard text response (expected for 'hello')")
                        
                else:
                    print(f"❌ Agent error: {response.status_code} - {response.text}")
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            
        await asyncio.sleep(1)  # Small delay between tests
    
    print("\n🎉 Test completed! If you see '✅ IFRAME DETECTED' messages above, the iframe functionality is working!")
    print("\n📋 Summary:")
    print("- The agent should respond with iframe configurations for chart/dashboard/form requests")
    print("- The demo UI will render these as actual iframes when both are running together")
    print("- Use 'localhost:10002' as the agent address in the demo UI to test interactively")


if __name__ == "__main__":
    asyncio.run(test_iframe_agent())