"""
Bob's Brain Foreman Agent Demo

Simplified foreman agent demonstrating task routing and delegation
to specialist workers using A2A protocol.

Based on: iam-senior-adk-devops-lead from Bob's Brain production system
Repository: https://github.com/jeremylongshore/bobs-brain
"""

from google.adk import LlmAgent
from typing import Dict, Any
import requests

# Configuration constants
WORKER_URL = "http://localhost:8001"
FOREMAN_PORT = 8000


def route_task(task: str, context: str = "") -> Dict[str, Any]:
    """
    Analyze a task and route it to the appropriate worker agent.

    In production Bob's Brain, this queries worker AgentCards to find
    the best match based on skills, then delegates via A2A protocol.

    Args:
        task: Task description (e.g., "analyze_adk_compliance")
        context: Additional context for the task

    Returns:
        Dict containing worker selection and delegation result
    """
    # Simplified worker discovery (in production, queries AgentCard discovery)
    # Fetch worker AgentCard to check capabilities
    try:
        agentcard = requests.get(f"{WORKER_URL}/.well-known/agent-card.json").json()
        worker_skills = [skill["id"] for skill in agentcard.get("skills", [])]
    except requests.exceptions.RequestException as e:
        return {"error": f"Worker discovery failed: {e}"}

    # Analyze task requirements
    if "compliance" in task.lower() or "adk" in task.lower():
        # Route to ADK compliance worker
        skill_to_use = "analyze_compliance"

        if skill_to_use not in worker_skills:
            return {"error": f"Worker doesn't have required skill: {skill_to_use}"}

        # Delegate to worker via A2A protocol
        try:
            response = requests.post(
                f"{WORKER_URL}/{skill_to_use}",
                json={"context": context}
            )
            return {
                "foreman": "iam_senior_adk_devops_lead_demo",
                "worker": agentcard.get("name", "unknown"),
                "task": task,
                "skill_used": skill_to_use,
                "result": response.json()
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Delegation failed: {e}"}

    return {"error": "No suitable worker found for task"}


def coordinate_workflow(workflow: str, steps: list) -> Dict[str, Any]:
    """
    Coordinate multi-step workflows across workers.

    In production, this orchestrates complex workflows like:
    - Issue detection → Plan creation → Implementation → QA → Documentation

    Args:
        workflow: Workflow name (e.g., "fix_compliance_issue")
        steps: List of workflow steps to execute

    Returns:
        Dict containing workflow execution results
    """
    results = []

    for step in steps:
        # In production, each step would be delegated to specialist workers
        # This demo shows the coordination pattern simplified
        results.append({
            "step": step,
            "status": "demo_executed",
            "note": "In production, delegated to specialist worker"
        })

    return {
        "workflow": workflow,
        "foreman": "iam_senior_adk_devops_lead_demo",
        "steps_completed": len(results),
        "results": results
    }


# Create the foreman agent
def get_foreman_agent() -> LlmAgent:
    """
    Create and configure the foreman agent.

    In production Bob's Brain, this includes:
    - System instruction defining foreman role
    - Access to 8 specialist worker AgentCards
    - Tools for GitHub, Terraform, etc.
    - Dual memory (Session + Memory Bank)
    """
    system_instruction = """You are the Foreman Agent for Bob's Brain (Demo Version).

Your role:
1. Receive complex tasks from users
2. Analyze task requirements
3. Query worker AgentCards to find specialists
4. Delegate to appropriate workers via A2A protocol
5. Aggregate results and respond

Available workers:
- iam_adk_demo: ADK compliance analysis and fixes

Production note: The full Bob's Brain has 8 specialist workers handling:
- ADK design, issues, fix plans, implementation, QA, docs, cleanup, indexing"""

    agent = LlmAgent(
        model="gemini-2.0-flash-exp",
        tools=[route_task, coordinate_workflow],
        system_instruction=system_instruction
    )

    return agent


def create_foreman_agentcard() -> Dict[str, Any]:
    """
    Create AgentCard for foreman agent (A2A Protocol 0.3.0).

    Published at /.well-known/agent-card.json for worker discovery.
    """
    return {
        "protocol_version": "0.3.0",
        "name": "iam_senior_adk_devops_lead_demo",
        "version": "0.1.0",
        "description": "Foreman agent demonstrating task routing and delegation pattern from Bob's Brain",
        "url": "http://localhost:8000",
        "preferred_transport": "HTTP",
        "spiffe_id": "spiffe://demo.intent.solutions/agent/foreman/dev/us-central1/0.1.0",
        "skills": [
            {
                "id": "route_task",
                "name": "Route Task",
                "description": "Analyze task and delegate to appropriate worker",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "context": {"type": "string"}
                    },
                    "required": ["task"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "worker": {"type": "string"},
                        "result": {"type": "object"}
                    }
                }
            },
            {
                "id": "coordinate_workflow",
                "name": "Coordinate Workflow",
                "description": "Orchestrate multi-step workflows across workers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow": {"type": "string"},
                        "steps": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["workflow", "steps"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "workflow": {"type": "string"},
                        "results": {"type": "array"}
                    }
                }
            }
        ]
    }


if __name__ == "__main__":
    from flask import Flask, jsonify, request

    app = Flask(__name__)
    agent = get_foreman_agent()

    @app.route("/.well-known/agent-card.json")
    def agentcard():
        return jsonify(create_foreman_agentcard())

    @app.route("/route_task", methods=["POST"])
    def handle_route_task():
        data = request.json
        return jsonify(route_task(data["task"], data.get("context", "")))

    @app.route("/coordinate_workflow", methods=["POST"])
    def handle_coordinate_workflow():
        data = request.json
        return jsonify(coordinate_workflow(data["workflow"], data["steps"]))

    print("🧠 Foreman Agent (Bob's Brain Demo) starting...")
    print("📋 AgentCard: http://localhost:8000/.well-known/agent-card.json")
    print("🔗 Production: https://github.com/jeremylongshore/bobs-brain")
    app.run(port=FOREMAN_PORT)
