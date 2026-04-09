import logging

from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
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
                '\nAttempting to fetch public agent card from: %s%s',
                base_url,
                AGENT_CARD_WELL_KNOWN_PATH,
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('\nSuccessfully fetched public agent card:')
            logger.info(_public_card)

        except Exception as e:
            logger.exception('\nCritical error fetching public agent card.')
            raise RuntimeError(
                '\nFailed to fetch the public agent card. Cannot continue.'
            ) from e

        print('\n--- Non-Streaming Call ---')
        # --8<-- [start:message_send]
        client_factory = ClientFactory(config=ClientConfig(streaming=False))
        client = client_factory.create(_public_card)
        logger.info('\nNon-streaming A2AClient initialized.')

        parts = [Part(text='Say hello.')]
        message = Message(
            role=Role.ROLE_USER,
            parts=parts,
            message_id=uuid4().hex,
        )
        request = SendMessageRequest(message=message)

        response = client.send_message(request)

        async for chunk in response:
            print('Response:')
            task, _ = chunk
            print(task)
        # --8<-- [end:message_send]

        print('\n--- Streaming Call ---')
        # --8<-- [start:message_stream]
        client_factory = ClientFactory(config=ClientConfig(streaming=True))
        streaming_client = client_factory.create(_public_card)
        logger.info('\nStreaming A2AClient initialized.')

        streaming_response = streaming_client.send_message(request)

        async for chunk in streaming_response:
            print('Response chunk:')
            task, _ = chunk
            print(task)
        # --8<-- [end:message_stream]

        print('\n--- Extended Card Call ---')
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
            except Exception:
                logger.exception('Failed to fetch extended agent card.')
        elif (
            _public_card
        ):  # supports_authenticated_extended_card is False or None
            logger.info(
                '\nPublic card does not indicate support for an extended card.'
            )

        await client.close()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
