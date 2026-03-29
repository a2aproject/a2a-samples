"""
DNAi Asha A2A Test Client
==========================
Demonstrates connecting to the hosted Asha medical agent via A2A protocol.

Usage:
    ASHA_API_KEY=your_key uv run test_client.py
"""

import json
import os
import sys

import httpx

BASE_URL = "https://api.askasha.org"
API_KEY = os.getenv("ASHA_API_KEY", "")


def discover():
    """Fetch and display the agent card."""
    with httpx.Client(timeout=10) as client:
        r = client.get(f"{BASE_URL}/.well-known/agent-card.json", params={"agent_id": "asha"})
        r.raise_for_status()
        card = r.json()

    print(f"Agent: {card['name']} v{card['version']}")
    print(f"Provider: {card['provider']['organization']}")
    print(f"Protocol: {card['supportedInterfaces'][0]['protocolVersion']}")
    print("Skills:")
    for skill in card["skills"]:
        print(f"  [{skill['id']}] {skill['name']}")
    if "epistemicCapabilities" in card:
        ec = card["epistemicCapabilities"]
        corpus = ec.get("knowledgeCorpus", {})
        print(f"Knowledge: {corpus.get('totalVectors', '?')} vectors, {len(corpus.get('collections', []))} collections")
    return card


def query(text: str) -> dict:
    """Send a medical question via A2A."""
    with httpx.Client(timeout=120) as client:
        r = client.post(
            f"{BASE_URL}/a2a/v1/message:send",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "message": {"role": "user", "parts": [{"text": text}]},
                "metadata": {"agent_id": "asha"},
            },
        )
        r.raise_for_status()
        return r.json()["task"]


def main():
    if not API_KEY:
        print("Set ASHA_API_KEY. Get a free key:")
        print("  curl -X POST https://api.askasha.org/api/a2a/signup \\")
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"email":"you@example.com","name":"Test","tier":"free"}\'')
        sys.exit(1)

    print("=" * 50)
    print("DNAi Asha — A2A Medical Agent")
    print("=" * 50)

    discover()

    print("\n--- Query ---")
    task = query("What are the interactions between warfarin and amiodarone?")
    print(f"State: {task['status']['state']}")

    for artifact in task.get("artifacts", []):
        if artifact.get("name") == "response" and artifact.get("parts"):
            print(f"Answer: {artifact['parts'][0]['text'][:300]}...")
        elif artifact.get("name") == "provenance" and artifact.get("parts"):
            prov = artifact["parts"][0].get("data", {})
            print(f"Sources: {prov.get('sources', [])}")
            print(f"Evidence: {prov.get('evidence_count', 0)} items")


if __name__ == "__main__":
    main()
