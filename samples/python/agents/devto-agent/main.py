# Import libraries
import asyncio
import logging
import traceback
from uuid import uuid4

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Assuming common types and client are importable
from a2a_servers.common.client import A2AClient, card_resolver # card_resolver might be needed
from a2a_servers.common.types import Message, TextPart, AgentCard # Import AgentCard if needed directly

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:10000/host_agent"

async def main():
    client = A2AClient(url=SERVER_URL)

    task_id = f"echo-task-{uuid4().hex}"
    session_id = f"session-{uuid4().hex}"

    while True:
        print("*" * 50)
        user_text = input("Enter your query: ")  # Example user input

        user_message = Message(
            role="user",
            parts=[TextPart(text=user_text)]
        )

        send_params = {
            "id": task_id,
            "sessionId": session_id,
            "message": user_message.model_dump(),
        }

        try:
            logger.info(f"Sending task {task_id} to {SERVER_URL}...")
            response = await client.send_task(payload=send_params)

            if response.error:
                logger.error(f"Task {task_id} failed: {response.error.message} (Code: {response.error.code})")
            elif response.result:
                task_result = response.result
                logger.info(f"Task {task_id} completed with state: {task_result.status.state}")
                if task_result.status.message and task_result.status.message.parts:
                    agent_part = task_result.status.message.parts[0]
                    print("\n")
                    print("------------- Agent Response -------------")
                    print("\n")
                    print(agent_part.text)
                else:
                    logger.warning("No message part in agent response status")
            else:
                logger.error(f"Received unexpected response for task {task_id}: {response}")

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"An error occurred while communicating with the agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())
