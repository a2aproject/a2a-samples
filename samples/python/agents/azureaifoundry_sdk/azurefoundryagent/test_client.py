"""Exercise the calendar agent through A2A 1.x JSON-RPC messaging."""

import asyncio
import logging
import os

import httpx

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest, TaskState
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict


logger = logging.getLogger(__name__)


async def main() -> None:
    """Send regular and streaming requests, reusing context for follow-up turns."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    base_url = os.getenv('A2A_BASE_URL', 'http://localhost:10007')
    queries = [
        'Hello! Can you help me with my calendar?',
        'Am I free tomorrow from 2 PM to 3 PM?',
        'What meetings do I have coming up today?',
        'Help me find the best time for a 1-hour meeting this week.',
        'Can you check my availability for next Tuesday afternoon?',
    ]

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        health = await http_client.get(f'{base_url}/health')
        health.raise_for_status()
        card = await A2ACardResolver(httpx_client=http_client, base_url=base_url).get_agent_card()
        logger.info('Connected to %s', card.name)

    for streaming in (False, True):
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            client = ClientFactory(
                ClientConfig(httpx_client=http_client, streaming=streaming)
            ).create(card)
            context_id = None
            async with client:
                for query in queries:
                    message = new_text_message(
                        query,
                        context_id=context_id,
                        role=Role.ROLE_USER,
                    )
                    logger.info('Sending message, streaming=%s: %s', streaming, query)
                    async for response in client.send_message(SendMessageRequest(message=message)):
                        logger.info('Response: %s', MessageToDict(response))
                        if response.HasField('task'):
                            context_id = response.task.context_id
                            status = response.task.status
                        elif response.HasField('status_update'):
                            context_id = response.status_update.context_id
                            status = response.status_update.status
                        elif response.HasField('message'):
                            context_id = response.message.context_id
                            continue
                        else:
                            continue
                        if status.state in (
                            TaskState.TASK_STATE_FAILED,
                            TaskState.TASK_STATE_REJECTED,
                        ):
                            raise RuntimeError(f'Agent task failed: {MessageToDict(status)}')


if __name__ == '__main__':
    asyncio.run(main())
