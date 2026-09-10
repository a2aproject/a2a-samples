import asyncio
import logging

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import display_agent_card, new_text_message
from a2a.types import (
    AgentCard,
    Role,
    SendMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _resolve_agent_card(httpx_client: httpx.AsyncClient, base_url: str) -> AgentCard:
    # --8<-- [start:A2ACardResolver]
    resolver = A2ACardResolver(
        httpx_client=httpx_client,
        base_url=base_url,
    )
    # --8<-- [end:A2ACardResolver]

    logger.info(
        'Attempting to fetch public agent card from: %s%s',
        base_url,
        AGENT_CARD_WELL_KNOWN_PATH,
    )
    public_card = await resolver.get_agent_card()
    logger.info('Successfully fetched public agent card:')
    display_agent_card(public_card)

    if public_card.capabilities.extended_agent_card:
        try:
            logger.info('Public card supports authenticated extended card.')
            auth_headers = {'Authorization': 'Bearer dummy-token-for-extended-card'}
            extended_card = await resolver.get_agent_card(
                http_kwargs={'headers': auth_headers},
            )
        except Exception:
            logger.exception('Failed to fetch extended agent card. Will proceed with public card.')
        else:
            logger.info('Successfully fetched authenticated extended agent card:')
            display_agent_card(extended_card)
            return extended_card

    return public_card


async def main() -> None:
    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        try:
            final_agent_card_to_use = await _resolve_agent_card(httpx_client, base_url)
        except Exception as e:
            logger.exception('Critical error fetching public agent card')
            raise RuntimeError('Failed to fetch the public agent card. Cannot continue.') from e

        # --8<-- [start:send_message]
        client = await create_client(
            agent=final_agent_card_to_use,
            client_config=ClientConfig(streaming=False, httpx_client=httpx_client),
        )
        logger.info('A2AClient initialized.')

        request = SendMessageRequest(
            message=new_text_message('how much is 10 USD in INR?', role=Role.ROLE_USER)
        )

        async for response in client.send_message(request):
            print(response)
        # --8<-- [end:send_message]

        # --8<-- [start:Multiturn]
        first_request = SendMessageRequest(
            message=new_text_message(
                'How much is the exchange rate for 1 USD?', role=Role.ROLE_USER
            )
        )

        task_id: str | None = None
        context_id: str | None = None

        async for response in client.send_message(first_request):
            if response.HasField('task'):
                task_id = response.task.id
                context_id = response.task.context_id
            elif response.HasField('status_update'):
                if response.status_update.task_id:
                    task_id = response.status_update.task_id
                if response.status_update.context_id:
                    context_id = response.status_update.context_id
            print(response)

        second_request = SendMessageRequest(
            message=new_text_message(
                'CAD',
                role=Role.ROLE_USER,
                task_id=task_id,
                context_id=context_id,
            )
        )

        async for second_response in client.send_message(second_request):
            print(second_response)
        # --8<-- [end:Multiturn]

        # --8<-- [start:send_message_streaming]
        streaming_client = await create_client(
            agent=final_agent_card_to_use,
            client_config=ClientConfig(streaming=True, httpx_client=httpx_client),
        )

        streaming_request = SendMessageRequest(
            message=new_text_message('how much is 10 USD in INR?', role=Role.ROLE_USER)
        )

        async for chunk in streaming_client.send_message(streaming_request):
            print(chunk)
        # --8<-- [end:send_message_streaming]

        await client.close()
        await streaming_client.close()


if __name__ == '__main__':
    asyncio.run(main())
