import logging  # Import the logging module

from uuid import uuid4

import grpc

from a2a.client import A2AGrpcClient
from a2a.grpc import a2a_pb2, a2a_pb2_grpc
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    Role,
    TextPart,
)
from a2a.utils import proto_utils


async def main() -> None:
    PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
    EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'

    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    base_url = '[::]:11001'

    async with grpc.aio.insecure_channel(base_url) as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                'Attempting to fetch public agent card from grpc endpoint'
            )
            proto_card = await stub.GetAgentCard(a2a_pb2.GetAgentCardRequest())
            logger.info('Successfully fetched agent card:')
            logger.info(proto_card)
            final_agent_card_to_user = proto_utils.FromProto.agent_card(
                proto_card
            )
        except Exception as e:
            logging.error('Failed to get agent card ', e)
            return

        client = A2AGrpcClient(stub, agent_card=final_agent_card_to_use)
        logger.info('A2AClient initialized.')

        request = MessageSendParams(
            message=Message(
                role=Role.user,
                parts=[Part(root=TextPart(text='roll a 5 sided dice'))],
                messageId=str(uuid4()),
            )
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        stream_response = client.send_message_streaming(request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
