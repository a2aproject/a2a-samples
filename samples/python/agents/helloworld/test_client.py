import logging

from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types import AgentCard
from a2a.types.a2a_pb2 import (
    GetExtendedAgentCardRequest,
    Message,
    Part,
    Role,
    SendMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    # --8<-- [start:A2ACardResolver]

    base_url = 'http://localhost:9999'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default
        )
        
        # --8<-- [end:A2ACardResolver]

        try:
            logger.info(
                f'\nAttempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('\nSuccessfully fetched public agent card:')
            logger.info(_public_card)
            logger.info(
                '\nUsing public agent card for client initialization.'
            )
            client_factory = ClientFactory(config=ClientConfig(streaming=False))
            client = client_factory.create(_public_card)
            logger.info('\nA2AClient initialized via ClientFactory.')

            if _public_card.capabilities.extended_agent_card:
                try:
                    logger.info(
                        '\nPublic card supports authenticated extended card. Attempting to fetch via Client.'
                    )
                    _extended_card = await client.get_extended_agent_card(
                        GetExtendedAgentCardRequest()
                    )
                    logger.info(
                        '\nSuccessfully fetched authenticated extended agent card:'
                    )
                    logger.info(_extended_card)

                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}.',
                        exc_info=True,
                    )
            elif (
                _public_card
            ):  # supports_authenticated_extended_card is False or None
                logger.info(
                    '\nPublic card does not indicate support for an extended card.'
                )

        except Exception as e:
            logger.error(
                f'\nCritical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                '\nFailed to fetch the public agent card. Cannot continue.'
            ) from e

        # --8<-- [start:send_message]

        parts = [Part(text='how much is 10 USD in INR?')]
        message = Message(
            role=Role.ROLE_USER,
            parts=parts,
            message_id=uuid4().hex,
        )
        request = SendMessageRequest(message=message)

        print('\nSend message response:')
        async for chunk in client.send_message(request):
            print(chunk)

        # --8<-- [end:send_message]

        # --8<-- [start:send_message_streaming]

        client._config.streaming = True

        print("\nStream response:")
        async for chunk in client.send_message(request):
            print(chunk)

        # --8<-- [end:send_message_streaming]

        await client.close()

if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
