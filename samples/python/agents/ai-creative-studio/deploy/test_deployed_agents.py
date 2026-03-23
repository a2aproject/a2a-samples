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

#!/usr/bin/env python3
"""
Test Deployed Agents - Complete Test Suite
Tests both specialist agents (Cloud Run) and orchestrator (Agent Engine)
"""

import asyncio
import os
import sys

import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "")
LOCATION = os.getenv("LOCATION", "us-central1")
AGENT_ENGINE_RESOURCE = os.getenv("AGENT_ENGINE_RESOURCE_NAME")

# Specialist agent URLs
SPECIALIST_AGENTS = {
    "Brand Strategist": os.getenv("STRATEGIST_AGENT_URL"),
    "Copywriter": os.getenv("COPYWRITER_AGENT_URL"),
    "Designer": os.getenv("DESIGNER_AGENT_URL"),
    "Critic": os.getenv("CRITIC_AGENT_URL"),
    "Project Manager": os.getenv("PM_AGENT_URL"),
}

# Test queries for each specialist
SPECIALIST_TESTS = {
    "Brand Strategist": """Analyze the market for eco-friendly water bottles targeting Gen-Z consumers.
    Focus on: competitors, trends, and target audience insights.""",
    "Copywriter": """Write 3 Instagram captions for an eco-friendly coffee brand called "GreenBrew".
    Target audience: environmentally conscious Gen-Z, 18-25 years old.
    Brand voice: authentic, playful, educational.""",
    "Designer": """Create visual concepts for 3 Instagram posts promoting sustainable fashion.
    Style: modern, minimalist, eco-friendly aesthetic.
    Color palette: earth tones with vibrant accents.""",
    "Critic": """Review this social media post:
    Caption: "Save the planet, one sip at a time! ☕🌍"
    Image: Coffee cup with leaves
    Target: Gen-Z, eco-conscious
    Platform: Instagram

    Provide constructive feedback on effectiveness and engagement potential.""",
    "Project Manager": """Create a project timeline for a 2-week social media campaign launch:
    - 5 Instagram posts
    - Target: Gen-Z
    - Budget: $5,000
    - Goal: Brand awareness
    Include key milestones and deliverables.""",
}

# Creative Director test query
ORCHESTRATOR_TEST = """Create a complete social media campaign for:
- Product: Eco-friendly coffee brand "GreenBrew"
- Target Audience: Gen-Z, environmentally conscious, 18-25 years old
- Platform: Instagram
- Goal: Brand awareness and drive website traffic
- Budget: $5,000
- Timeline: Launch in 2 weeks
- Brand Voice: Authentic, playful, educational

Create: market research, 3 posts with copy, visual concepts, and project timeline."""


def print_header(title: str, char="="):
    """Print formatted header"""
    print(f"\n{char * 70}")
    print(f"{title}")
    print(f"{char * 70}\n")


async def test_specialist_a2a(name: str, url: str, query: str) -> bool:
    """Test a specialist agent via A2A protocol"""
    if not url:
        print("  ⚠️  Skipped: No URL configured")
        return False

    print(f"  URL: {url}")
    print(f"  Query: {query[:80]}...")

    try:
        # Import required modules
        from google.adk import Runner
        from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        # Create remote agent
        remote_agent = RemoteA2aAgent(
            name=name.lower().replace(" ", "_"),
            description=f"Test connection to {name}",
            agent_card=f"{url}/.well-known/agent.json",
        )

        print("  ⏳ Calling agent...")

        # Create session service and runner
        session_service = InMemorySessionService()
        runner = Runner(
            app_name="test", agent=remote_agent, session_service=session_service
        )

        # Create session
        session_id = f"test_session_{name.lower().replace(' ', '_')}"
        user_id = "test_user"

        await session_service.create_session(
            app_name="test", user_id=user_id, session_id=session_id
        )

        # Run agent and collect response
        response_text = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text=query)]),
        ):
            if hasattr(event, "text") and event.text:
                response_text.append(event.text)
            elif hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text.append(part.text)

        # Clean up
        await runner.close()

        full_response = "".join(response_text)
        print(f"  ✓ Response received ({len(full_response)} chars)")
        print(f"  Preview: {full_response[:200]}...")

        return True

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_orchestrator(resource_name: str, query: str) -> bool:
    """Test Creative Director orchestrator on Agent Engine"""
    if not resource_name:
        print("  ⚠️  No AGENT_ENGINE_RESOURCE_NAME found in .env")
        return False

    print(f"  Resource: {resource_name}")
    print(f"  Query: {query[:80]}...")

    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)

        # Connect to deployed agent
        remote_app = agent_engines.get(resource_name)
        print("  ✓ Connected to Agent Engine")

        # Create session
        session = await remote_app.async_create_session(user_id="test_user")
        print(f"  ✓ Session created: {session['id']}")

        # Stream query
        print("  ⏳ Streaming response...\n")
        print("  " + "─" * 66)

        response_parts = []
        async for event in remote_app.async_stream_query(
            user_id="test_user",
            session_id=session["id"],
            message=query,
        ):
            content = event.get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                if part.get("text") and not part.get("function_call"):
                    text = part["text"]
                    print(f"  {text}")
                    response_parts.append(text)
                elif part.get("function_call"):
                    func_name = part.get("function_call", {}).get("name", "unknown")
                    print(f"  🔧 Tool call: {func_name}")

        print("  " + "─" * 66)
        print(f"  ✓ Complete! Received {len(response_parts)} response parts")

        return True

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_all_specialists():
    """Test all specialist agents"""
    print_header("Testing Specialist Agents (Cloud Run)")

    results = {}
    for name, url in SPECIALIST_AGENTS.items():
        print(f"🧪 Testing: {name}")

        if name not in SPECIALIST_TESTS:
            print("  ⚠️  No test query defined")
            results[name] = False
            continue

        query = SPECIALIST_TESTS[name]
        success = await test_specialist_a2a(name, url, query)
        results[name] = success
        print()

    return results


async def test_orchestrator_only():
    """Test Creative Director orchestrator"""
    print_header("Testing Creative Director Orchestrator (Agent Engine)")

    print("🧪 Testing: Creative Director")
    success = await test_orchestrator(AGENT_ENGINE_RESOURCE, ORCHESTRATOR_TEST)

    return {"Creative Director": success}


async def test_all():
    """Run complete test suite"""
    print_header("AI Creative Studio - Complete Test Suite", "=")

    print(f"Project: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print()

    # Test specialists
    specialist_results = await test_all_specialists()

    # Test orchestrator
    orchestrator_results = await test_orchestrator_only()

    # Combine results
    all_results = {**specialist_results, **orchestrator_results}

    # Summary
    print_header("Test Results Summary", "=")

    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)

    for name, success in all_results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")

    print()
    print(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test deployed AI Creative Studio agents"
    )
    parser.add_argument(
        "--test",
        choices=["all", "specialists", "orchestrator"],
        default="all",
        help="Which agents to test",
    )
    parser.add_argument(
        "--agent",
        choices=list(SPECIALIST_AGENTS.keys()),
        help="Test specific specialist agent only",
    )

    args = parser.parse_args()

    if args.agent:
        # Test specific agent
        print_header(f"Testing: {args.agent}", "=")
        url = SPECIALIST_AGENTS[args.agent]
        query = SPECIALIST_TESTS.get(args.agent, "Test query")
        success = await test_specialist_a2a(args.agent, url, query)
        return 0 if success else 1

    elif args.test == "specialists":
        results = await test_all_specialists()
        passed = sum(1 for v in results.values() if v)
        return 0 if passed == len(results) else 1

    elif args.test == "orchestrator":
        results = await test_orchestrator_only()
        return 0 if results["Creative Director"] else 1

    else:
        # Test all
        return await test_all()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
