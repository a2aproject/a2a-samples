import asyncio


async def main() -> None:
    print('Initializes the A2ACardResolver instance with an HTTP client')
    # --8<-- [start:A2ACardResolver]
    import httpx  # noqa: PLC0415

    from a2a.client import A2ACardResolver  # noqa: PLC0415
    from a2a.helpers import display_agent_card  # noqa: PLC0415

    # Initializes the A2ACardResolver instance with an HTTP client, base URL,
    # and uses the default path for the agent card.
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url='http://127.0.0.1:9999',
            # Provide agent_card_path, if your agent uses a different path
            # agent_card_path=''  # noqa: ERA001
        )

        # --8<-- [end:A2ACardResolver]
        public_agent_card = await resolver.get_agent_card()

        print('\nSuccessfully fetched the public agent card:')
        display_agent_card(public_agent_card)

        print('\n--- Public Agent Card - Non-Streaming Call ---')
        # --8<-- [start:message_send]
        from a2a.client import ClientConfig, create_client  # noqa: PLC0415
        from a2a.helpers import new_text_message  # noqa: PLC0415
        from a2a.types.a2a_pb2 import (  # noqa: PLC0415
            GetExtendedAgentCardRequest,
            Role,
            SendMessageRequest,
        )

        print('\nInitializing a non-streaming client.')
        config = ClientConfig(streaming=False)
        client = await create_client(
            agent=public_agent_card, client_config=config
        )

        # Creates a new text message to be sent to the A2A Server.
        message = new_text_message('Say hello.', role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print('Response:')
        async for chunk in client.send_message(request):
            print(chunk)
        # --8<-- [end:message_send]

        print('\n--- Public Agent Card - Streaming Call ---')
        # --8<-- [start:message_stream]
        print('\nInitializing a streaming client.')
        streaming_config = ClientConfig(streaming=True)
        streaming_client = await create_client(
            agent=public_agent_card, client_config=streaming_config
        )

        print('Response:')
        async for chunk in streaming_client.send_message(request):
            print(chunk)
        # --8<-- [end:message_stream]

        await streaming_client.close()

        print('\n--- Extended Agent Card - Non-Streaming Call ---')
        extended_card = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest()
        )
        print('\nSuccessfully fetched the authenticated extended agent card:')
        display_agent_card(extended_card)

        await client.close()


if __name__ == '__main__':

    asyncio.run(main())
