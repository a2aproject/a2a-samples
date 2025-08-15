import asyncio
import uuid

from src.a2a.a2a_client import A2ASimpleClient


async def main():
    a2a_client: A2ASimpleClient = A2ASimpleClient()
    agent_host_url = "http://localhost:8000/a2a"

    trending_task = a2a_client.create_task(agent_url=f'{agent_host_url}/trending', message="What's trending today?",
                                           context_id=str(uuid.uuid4()))
    analysis_task = a2a_client.create_task(agent_url=f"{agent_host_url}/analyzer",
                                           message="Analyze the trend AI in Social Media", context_id=str(uuid.uuid4()))

    trending_topics, analysis = await asyncio.gather(trending_task, analysis_task)
    print(trending_topics)
    print(analysis)

    print("###############################################################################################################")
    print("Multi-turn conversation with an agent............................")
    context_id = str(uuid.uuid4())
    print(f"Starting conversation with context_id: {context_id}")

    # Turn 1 — Start conversation
    conversation_task = await a2a_client.create_task(
        agent_url=f"{agent_host_url}/conversation",
        message="Who is the Prime Minister of India?",
        context_id=context_id
    )
    print(f"Turn 1 → {conversation_task} \n\n")

    # Turn 2 — Follow-up using pronoun (tests context memory)
    conversation_task = await a2a_client.create_task(
        agent_url=f"{agent_host_url}/conversation",
        message="What is his wife's name?",
        context_id=context_id
    )
    print(f"Turn 2 → {conversation_task} \n\n")

    # Turn 3 — Another contextual follow-up
    conversation_task = await a2a_client.create_task(
        agent_url=f"{agent_host_url}/conversation",
        message="How many children do they have?",
        context_id=context_id
    )
    print(f"Turn 3 → {conversation_task} \n\n")

    # Turn 4 — A context shift
    conversation_task = await a2a_client.create_task(
        agent_url=f"{agent_host_url}/conversation",
        message="List three major policies he introduced.",
        context_id=context_id
    )
    print(f"Turn 4 → {conversation_task}")


if __name__ == "__main__":
    asyncio.run(main())
