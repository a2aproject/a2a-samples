#!/usr/bin/env python3
"""Error handling example with the Hello World Azure AI Foundry Agent."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_world_agent.hello_agent import HelloWorldAgent
from hello_world_agent.utils import setup_logging, validate_environment, format_error_message


async def test_missing_credentials():
    """Test behavior when credentials are missing."""
    print("\n🧪 Test 1: Missing Credentials")
    print("-" * 35)
    
    # Temporarily remove credentials
    original_endpoint = os.environ.get('AZURE_AI_FOUNDRY_PROJECT_ENDPOINT')
    original_model = os.environ.get('AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME')
    
    # Remove environment variables
    if 'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT' in os.environ:
        del os.environ['AZURE_AI_FOUNDRY_PROJECT_ENDPOINT']
    if 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME' in os.environ:
        del os.environ['AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME']
    
    try:
        agent = HelloWorldAgent()
        await agent.create_agent()
        print("❌ Expected error but none occurred")
    except KeyError as e:
        print(f"✅ Correctly caught missing environment variable: {e}")
    except Exception as e:
        print(f"⚠️  Got unexpected error: {format_error_message(e)}")
    finally:
        # Restore environment variables
        if original_endpoint:
            os.environ['AZURE_AI_FOUNDRY_PROJECT_ENDPOINT'] = original_endpoint
        if original_model:
            os.environ['AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'] = original_model


async def test_invalid_endpoint():
    """Test behavior with an invalid endpoint."""
    print("\n🧪 Test 2: Invalid Endpoint")
    print("-" * 30)
    
    # Temporarily set invalid endpoint
    original_endpoint = os.environ.get('AZURE_AI_FOUNDRY_PROJECT_ENDPOINT')
    os.environ['AZURE_AI_FOUNDRY_PROJECT_ENDPOINT'] = 'https://invalid-endpoint.com/'
    
    try:
        agent = HelloWorldAgent()
        await agent.create_agent()
        print("❌ Expected error but none occurred")
    except Exception as e:
        error_msg = format_error_message(e)
        print(f"✅ Correctly caught invalid endpoint error:")
        print(f"   {error_msg}")
    finally:
        # Restore original endpoint
        if original_endpoint:
            os.environ['AZURE_AI_FOUNDRY_PROJECT_ENDPOINT'] = original_endpoint


async def test_graceful_cleanup():
    """Test graceful cleanup after errors."""
    print("\n🧪 Test 3: Graceful Cleanup")
    print("-" * 28)
    
    agent = HelloWorldAgent()
    
    try:
        # This might fail, but cleanup should still work
        print("🔧 Attempting to create agent...")
        await agent.create_agent()
        print("✅ Agent created successfully")
        
        # Simulate some error during operation
        print("💥 Simulating an error...")
        raise ValueError("Simulated error for testing cleanup")
        
    except ValueError as e:
        print(f"✅ Caught simulated error: {e}")
    except Exception as e:
        print(f"⚠️  Caught unexpected error: {format_error_message(e)}")
    finally:
        print("🧹 Testing cleanup...")
        try:
            await agent.cleanup_agent()
            print("✅ Cleanup completed successfully")
        except Exception as e:
            print(f"❌ Cleanup failed: {format_error_message(e)}")


async def test_environment_validation():
    """Test environment validation utility."""
    print("\n🧪 Test 4: Environment Validation")
    print("-" * 35)
    
    # Test with current environment
    result = validate_environment()
    
    if result["valid"]:
        print("✅ Environment validation passed")
        if result["warnings"]:
            print("⚠️  Warnings:")
            for warning in result["warnings"]:
                print(f"   - {warning}")
    else:
        print("❌ Environment validation failed")
        print("Missing variables:")
        for var in result["missing_vars"]:
            print(f"   - {var}")


async def error_handling_example():
    """Run all error handling tests."""
    print("🚨 Error Handling Example")
    print("=" * 40)
    print("This example demonstrates various error scenarios and how to handle them gracefully.")
    
    await test_environment_validation()
    await test_missing_credentials()
    await test_invalid_endpoint()
    await test_graceful_cleanup()
    
    print("\n✅ Error handling examples completed!")
    print("💡 Key takeaways:")
    print("   - Always validate environment variables before starting")
    print("   - Use try/except blocks around agent operations")
    print("   - Always clean up resources in finally blocks")
    print("   - Provide user-friendly error messages")


async def main():
    """Main function."""
    setup_logging("ERROR")  # Only show errors for cleaner output
    await error_handling_example()


if __name__ == "__main__":
    asyncio.run(main())
