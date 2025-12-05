"""
Bob's Brain Orchestrator Agent

Global orchestrator demonstrating LLM-based reasoning and A2A delegation
to foreman agents using the ADK framework.

Based on: bob from Bob's Brain production system
Repository: https://github.com/jeremylongshore/bobs-brain
"""

from google.adk import LlmAgent
from google.adk.sessions import VertexAiSessionService
from google.adk.memory import VertexAiMemoryBankService
from typing import Dict, Any
import requests
import os

# Configuration constants
BOB_PORT = 8002
FOREMAN_URL = "http://localhost:8000"
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "demo-project")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

# Memory configuration (for production with real GCP project)
ENABLE_MEMORY = os.getenv("ENABLE_MEMORY", "false").lower() == "true"


def call_foreman(task: str, context: str = "") -> Dict[str, Any]:
    """
    Delegate complex tasks to the foreman agent via A2A protocol.

    Bob uses this tool when he determines a task requires departmental
    expertise (ADK compliance, DevOps, infrastructure work).

    Args:
        task: Natural language description of what needs to be done
        context: Additional context or constraints for the task

    Returns:
        Dict containing foreman's response and any results from workers
    """
    try:
        # First, discover foreman's capabilities via AgentCard
        agentcard_response = requests.get(f"{FOREMAN_URL}/.well-known/agent-card.json")
        agentcard = agentcard_response.json()

        # Send task to foreman for processing
        # The foreman will use its LlmAgent to analyze and route appropriately
        response = requests.post(
            f"{FOREMAN_URL}/task",
            json={
                "user_input": f"Task: {task}\n\nContext: {context}",
                "session_id": "bob-to-foreman"  # In production, use actual session tracking
            }
        )

        return {
            "orchestrator": "bob_demo",
            "foreman": agentcard.get("name", "unknown"),
            "task": task,
            "foreman_response": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "orchestrator": "bob_demo",
            "error": f"Failed to reach foreman: {e}",
            "suggestion": "Ensure foreman agent is running on localhost:8000"
        }


def get_bob_agent() -> LlmAgent:
    """
    Create and configure Bob, the global orchestrator agent.

    Bob's responsibilities:
    - Interface with users via natural language
    - Understand high-level goals and break them into tasks
    - Delegate to foreman when specialized expertise is needed
    - Aggregate results and provide coherent responses
    - Maintain conversation context via memory

    In production Bob's Brain:
    - Bob interfaces with Slack for user communication
    - Memory integration tracks conversation context
    - Tools include GitHub, documentation, and foreman delegation
    """
    system_instruction = """You are Bob, the Global Orchestrator for the ADK Compliance Department (Demo Version).

Your role:
1. Understand user requests in natural language
2. Determine if tasks require specialized expertise
3. Delegate to the foreman agent for ADK/DevOps/infrastructure work
4. Aggregate and synthesize results from the foreman
5. Provide clear, helpful responses to users

Available delegation:
- call_foreman: Delegate to the department foreman for ADK compliance, architecture reviews,
  infrastructure work, or any technical task requiring specialist knowledge

Decision framework:
- Simple questions about ADK → Answer directly if you have the knowledge
- Complex analysis, code review, infrastructure → Delegate to foreman
- Multi-step workflows requiring specialists → Delegate to foreman
- User wants to understand something → You explain, but delegate for deep analysis

Your communication style:
- Clear and concise
- Professional but approachable
- Explain what you're doing when delegating
- Synthesize technical details into actionable insights

Production note: The full Bob's Brain system has:
- Slack integration for user communication
- Access to GitHub, documentation repositories, and Vertex AI Search
- Dual memory (Session + Memory Bank) for context retention
- 8 specialist workers coordinated by the foreman"""

    # Create agent with memory integration (if enabled)
    agent_config = {
        "model": "gemini-2.0-flash-exp",
        "tools": [call_foreman],
        "system_instruction": system_instruction
    }

    # Add memory services if GCP project is configured
    if ENABLE_MEMORY and GCP_PROJECT_ID != "demo-project":
        agent_config["session_service"] = VertexAiSessionService(
            project_id=GCP_PROJECT_ID,
            location=GCP_REGION
        )
        agent_config["memory_bank_service"] = VertexAiMemoryBankService(
            project_id=GCP_PROJECT_ID,
            location=GCP_REGION
        )

    agent = LlmAgent(**agent_config)
    return agent


def create_bob_agentcard() -> Dict[str, Any]:
    """
    Create AgentCard for Bob orchestrator (A2A Protocol 0.3.0).

    Published at /.well-known/agent-card.json for external discovery.
    """
    return {
        "protocol_version": "0.3.0",
        "name": "bob_demo",
        "version": "0.1.0",
        "description": "Global orchestrator demonstrating LLM-based reasoning and A2A delegation from Bob's Brain",
        "url": "http://localhost:8002",
        "preferred_transport": "HTTP",
        "spiffe_id": "spiffe://demo.intent.solutions/agent/bob/dev/us-central1/0.1.0",
        "capabilities": ["orchestration", "natural_language_interface", "foreman_delegation"],
        "skills": [
            {
                "id": "process_request",
                "name": "Process User Request",
                "description": "Analyze user request and orchestrate appropriate response via delegation or direct answer",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_input": {"type": "string", "description": "Natural language user request"},
                        "session_id": {"type": "string", "description": "Session tracking ID"}
                    },
                    "required": ["user_input"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "delegated_to": {"type": "string"},
                        "actions_taken": {"type": "array"}
                    }
                }
            }
        ]
    }


if __name__ == "__main__":
    from flask import Flask, jsonify, request

    app = Flask(__name__)
    agent = get_bob_agent()

    @app.route("/.well-known/agent-card.json")
    def agentcard():
        return jsonify(create_bob_agentcard())

    @app.route("/task", methods=["POST"])
    def handle_task():
        """
        Main entrypoint for Bob orchestrator.

        Receives user requests in natural language and uses LlmAgent.run()
        to determine appropriate action (direct answer or delegation).
        """
        data = request.json
        user_input = data.get("user_input", "")
        session_id = data.get("session_id", "default")

        if not user_input:
            return jsonify({"error": "user_input is required"}), 400

        # Use LlmAgent.run() - this is where the LLM reasoning happens!
        # The agent will analyze the input and decide whether to:
        # 1. Answer directly
        # 2. Call call_foreman tool to delegate
        response = agent.run(
            user_input=user_input,
            session_id=session_id if ENABLE_MEMORY else None
        )

        return jsonify({
            "orchestrator": "bob_demo",
            "user_input": user_input,
            "response": response,
            "note": "Bob used LlmAgent.run() to process this request"
        })

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "agent": "bob_demo",
            "memory_enabled": ENABLE_MEMORY,
            "foreman_url": FOREMAN_URL
        })

    print("🧠 Bob Orchestrator (Global Coordinator) starting...")
    print(f"📋 AgentCard: http://localhost:{BOB_PORT}/.well-known/agent-card.json")
    print(f"🔗 Foreman URL: {FOREMAN_URL}")
    print(f"💾 Memory: {'Enabled' if ENABLE_MEMORY else 'Disabled (set ENABLE_MEMORY=true and GCP_PROJECT_ID)'}")
    print("🔗 Production: https://github.com/jeremylongshore/bobs-brain")
    print("\nExample usage:")
    print(f'curl -X POST http://localhost:{BOB_PORT}/task \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"user_input": "Analyze our ADK agent for compliance issues"}\'')
    app.run(port=BOB_PORT)
