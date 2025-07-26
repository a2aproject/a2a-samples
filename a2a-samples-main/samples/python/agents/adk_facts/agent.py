from google.adk.agents.remote_a2a_agent import RemoteA2aAgent


root_agent = RemoteA2aAgent(
    name="facts_agent",
    description="Agent to give interesting facts.",
    agent_card=("http://localhost:8001/a2a/facts_agent/.well-known/agent.json"),
)
