import logging  # Import the logging module

from uuid import uuid4

import asyncclick as click
import grpc
import httpx

from a2a.client import A2ACardResolver, A2AGrpcClient
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


@click.command()
@click.option('--agent-card-url', 'agent_card_url', default='http://localhost:11000')
@click.option('--grpc-endpoint', 'grpc_endpoint', default=None)
async def main(agent_card_url: str, grpc_endpoint: str | None) -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    if grpc_endpoint is None:
        logger.info('gRPC endpoint not specified. Fetching public agent card from HTTP server')
        # if grpc_url is not specified, try to fetch the public agent card
        agent_card = await get_public_agent_card(agent_card_url)
        base_url = agent_card.url
    else:
        logger.info('gRPC endpoint specified. Skip fetching the public agent card from HTTP server')
        #if grpc endpoint is specific
        base_url = grpc_endpoint


    async with grpc.aio.insecure_channel(base_url) as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)

        # use the gRPC channel to get the authenticated agent card
        # in real-word applications, agent_card.supports_authenticated_extended_card flag
        # specifies if authenticated card should be fetched.
        # If an authenticated agent card is provided, client should use it for interacting with the gRPC service
        try:
            if agent_card.supports_authenticated_extended_card:
                logger.info(
                    'Attempting to fetch authenticated agent card from grpc endpoint'
                )
                proto_card = await stub.GetAgentCard(a2a_pb2.GetAgentCardRequest())
                logger.info('Successfully fetched agent card:')
                logger.info(proto_card)
                final_agent_card_to_use = proto_utils.FromProto.agent_card(
                    proto_card
                )
            else:
                final_agent_card_to_use = agent_card
        except Exception:
            logging.exception('Failed to get authenticated agent card. Exiting.')
            return


        client = A2AGrpcClient(stub, agent_card=final_agent_card_to_use)
        logger.info('A2AClient initialized.')

        request = MessageSendParams(
            message=Message(
                role=Role.user,
                parts=[Part(root=TextPart(text='roll a 5 sided dice'))],
                message_id=str(uuid4()),
            )
        )

        response = await client.send_message(request)
        logging.info(response.model_dump(mode='json', exclude_none=True))

        stream_response = client.send_message_streaming(request)

        async for chunk in stream_response:
            logging.info(chunk.model_dump(mode='json', exclude_none=True))

async def get_public_agent_card(agent_card_url: str) -> AgentCard:
    agent_card: AgentCard | None = None
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=agent_card_url,
        )
        # Fetch the base agent card
        agent_card = await resolver.get_agent_card()

    if not agent_card:
        raise ValueError('Public agent card not found')

    return agent_card


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
