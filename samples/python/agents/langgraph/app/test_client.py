import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import display_agent_card, new_text_message
from a2a.types.a2a_pb2 import (
    GetExtendedAgentCardRequest,
    Role,
    SendMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


async def main() -> None:
    # --8<-- [start:A2ACardResolver]
    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default
        )

        # --8<-- [end:A2ACardResolver]

        print(
            f'Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
        )
        public_card = await resolver.get_agent_card()
        print('\nSuccessfully fetched public agent card:')
        display_agent_card(public_card)

        print('\n--- Non-Streaming Call ---')
        # --8<-- [start:send_message]
        config = ClientConfig(streaming=False)
        client = await create_client(agent=public_card, client_config=config)
        print('\nNon-streaming Client initialized.')

        message = new_text_message('how much is 10 USD in INR?', role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print('Response:')
        async for chunk in client.send_message(request):
            print(chunk)
        # --8<-- [end:send_message]

        print('\n--- Multiturn Call ---')
        # --8<-- [start:Multiturn]
        message = new_text_message(
            'How much is the exchange rate for 1 USD?', role=Role.ROLE_USER
        )
        request = SendMessageRequest(message=message)

        task_id = None
        context_id = None
        async for chunk in client.send_message(request):
            print(chunk)
            if chunk.HasField('task'):
                task_id = chunk.task.id
                context_id = chunk.task.context_id

        if task_id and context_id:
            second_message = new_text_message(
                'CAD',
                role=Role.ROLE_USER,
                task_id=task_id,
                context_id=context_id,
            )
            second_request = SendMessageRequest(message=second_message)

            print('Second turn response:')
            async for chunk in client.send_message(second_request):
                print(chunk)
        # --8<-- [end:Multiturn]

        print('\n--- Streaming Call ---')
        # --8<-- [start:send_message_streaming]
        streaming_config = ClientConfig(streaming=True)
        streaming_client = await create_client(
            agent=public_card, client_config=streaming_config
        )
        print('\nStreaming Client initialized.')

        stream_message = new_text_message(
            'how much is 10 USD in INR?', role=Role.ROLE_USER
        )
        streaming_request = SendMessageRequest(message=stream_message)

        async for chunk in streaming_client.send_message(streaming_request):
            print('Response chunk:')
            print(chunk)
        # --8<-- [end:send_message_streaming]

        await streaming_client.close()

        print('\n--- Extended Card Call ---')
        if public_card.capabilities.extended_agent_card:
            extended_card = await client.get_extended_agent_card(
                GetExtendedAgentCardRequest()
            )
            print('\nSuccessfully fetched authenticated extended agent card:')
            display_agent_card(extended_card)

        await client.close()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
