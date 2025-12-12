"""
Bob's Brain Worker Agent Demo

Simplified ADK compliance worker demonstrating specialist task execution
in a foreman-worker architecture.

Based on: iam-adk from Bob's Brain production system
Repository: https://github.com/jeremylongshore/bobs-brain
"""

from google.adk import LlmAgent
from typing import Dict, Any

# Configuration constants
WORKER_PORT = 8001
PENALTY_PER_ISSUE = 20  # Compliance score penalty for each issue found


def analyze_compliance(context: str) -> Dict[str, Any]:
    """
    Analyze code or configuration for ADK compliance.

    In production Bob's Brain, this checks against Hard Mode rules (R1-R8)
    and 28 canonical standards using Vertex AI Search for documentation.

    Args:
        context: Code, config, or documentation to analyze

    Returns:
        Dict containing compliance analysis results
    """
    # Simplified compliance check (production uses full ADK spec + 6767 standards)
    issues = []
    suggestions = []

    # Check for common ADK patterns
    if "google-adk" not in context.lower():
        issues.append({
            "type": "dependency",
            "message": "Missing google-adk import",
            "severity": "high"
        })
        suggestions.append("Add: from google.adk import LlmAgent")

    if "LlmAgent" not in context:
        issues.append({
            "type": "agent_initialization",
            "message": "No LlmAgent found",
            "severity": "medium"
        })
        suggestions.append("Create agent using ADK LlmAgent class")

    return {
        "analysis_type": "adk_compliance",
        "context_analyzed": len(context),
        "issues_found": len(issues),
        "issues": issues,
        "suggestions": suggestions,
        "compliance_score": max(0, 100 - (len(issues) * PENALTY_PER_ISSUE)),
        "worker": "iam_adk_demo",
        "note": "Production analysis uses 28 canonical standards and full ADK spec"
    }


def suggest_fix(issue: str, context: str = "") -> Dict[str, Any]:
    """
    Suggest fixes for ADK compliance issues.

    In production, this generates detailed fix plans with:
    - File paths and line numbers
    - Code snippets with changes
    - Documentation references
    - Related standards

    Args:
        issue: Description of the compliance issue
        context: Additional context about the codebase

    Returns:
        Dict containing fix suggestions
    """
    # Simplified fix suggestion (production has comprehensive fix templates)
    fixes = []

    if "import" in issue.lower():
        fixes.append({
            "file": "agent.py",
            "change": "Add ADK imports at top of file",
            "code_snippet": "from google.adk import LlmAgent, Tool",
            "standard": "6767-DR-STND-adk-agent-engine-spec-and-hardmode-rules.md"
        })

    if "agent" in issue.lower():
        fixes.append({
            "file": "agent.py",
            "change": "Create LlmAgent instance",
            "code_snippet": '''def get_agent() -> LlmAgent:
    return LlmAgent(
        model="gemini-2.0-flash-exp",
        tools=[...],
        system_instruction="..."
    )''',
            "standard": "6767-LAZY-DR-STND-adk-lazy-loading-app-pattern.md"
        })

    return {
        "issue": issue,
        "fixes_available": len(fixes),
        "fixes": fixes,
        "worker": "iam_adk_demo",
        "note": "Production fix plans include complete code changes and test cases"
    }


# Create the worker agent
def get_worker_agent() -> LlmAgent:
    """
    Create and configure the ADK compliance worker agent.

    In production Bob's Brain, this includes:
    - Access to Vertex AI Search with ADK documentation
    - Tools for file system access
    - Memory integration for conversation context
    - Comprehensive standards library (28 canonical docs)
    """
    system_instruction = """You are an ADK Compliance Worker (Demo Version).

Your role:
1. Receive tasks from the foreman agent
2. Analyze code/config for ADK compliance
3. Suggest fixes aligned with Google ADK best practices
4. Report results back to foreman

Expertise areas:
- Google Agent Development Kit (ADK) patterns
- Vertex AI Agent Engine deployment
- Hard Mode rules (R1-R8) compliance
- Agent Factory architecture

Production note: The full iam-adk agent has access to:
- Vertex AI Search with complete ADK documentation
- 28 canonical standards (6767 series)
- GitHub API for code analysis
- Terraform tools for infrastructure checks"""

    agent = LlmAgent(
        model="gemini-2.0-flash-exp",
        tools=[analyze_compliance, suggest_fix],
        system_instruction=system_instruction
    )

    return agent


def create_worker_agentcard() -> Dict[str, Any]:
    """
    Create AgentCard for worker agent (A2A Protocol 0.3.0).

    Published at /.well-known/agent-card.json for foreman discovery.
    """
    return {
        "protocol_version": "0.3.0",
        "name": "iam_adk_demo",
        "version": "0.1.0",
        "description": "ADK compliance worker demonstrating specialist task execution from Bob's Brain",
        "url": "http://localhost:8001",
        "preferred_transport": "HTTP",
        "spiffe_id": "spiffe://demo.intent.solutions/agent/adk-worker/dev/us-central1/0.1.0",
        "capabilities": ["adk_expertise", "compliance_analysis", "fix_suggestions"],
        "skills": [
            {
                "id": "analyze_compliance",
                "name": "Analyze Compliance",
                "description": "Check code/config against ADK standards and Hard Mode rules",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "context": {"type": "string", "description": "Code or config to analyze"}
                    },
                    "required": ["context"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "compliance_score": {"type": "number"},
                        "issues": {"type": "array"},
                        "suggestions": {"type": "array"}
                    }
                }
            },
            {
                "id": "suggest_fix",
                "name": "Suggest Fix",
                "description": "Provide detailed fix suggestions for compliance issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "context": {"type": "string"}
                    },
                    "required": ["issue"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "fixes": {"type": "array"},
                        "code_snippet": {"type": "string"}
                    }
                }
            }
        ]
    }


if __name__ == "__main__":
    from flask import Flask, jsonify, request

    app = Flask(__name__)
    agent = get_worker_agent()

    @app.route("/.well-known/agent-card.json")
    def agentcard():
        return jsonify(create_worker_agentcard())

    @app.route("/analyze_compliance", methods=["POST"])
    def handle_analyze_compliance():
        data = request.json
        return jsonify(analyze_compliance(data["context"]))

    @app.route("/suggest_fix", methods=["POST"])
    def handle_suggest_fix():
        data = request.json
        return jsonify(suggest_fix(data["issue"], data.get("context", "")))

    print("🔧 Worker Agent (ADK Compliance Demo) starting...")
    print("📋 AgentCard: http://localhost:8001/.well-known/agent-card.json")
    print("🔗 Production: https://github.com/jeremylongshore/bobs-brain")
    app.run(port=WORKER_PORT)
