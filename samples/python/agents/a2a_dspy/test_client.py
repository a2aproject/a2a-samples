import logging

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    # --8<-- [start:A2ACardResolver]

    base_url = 'http://localhost:10020'
    
    # Each user gets their own isolated memory space
    ctx_id = str(uuid4())
    # Create httpx client with authentication headers and no timeout
    async with httpx.AsyncClient(timeout=None) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        # --8<-- [end:A2ACardResolver]

        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('Successfully fetched public agent card:')
            logger.info(
                _public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = _public_card
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

            if _public_card.supports_authenticated_extended_card:
                try:
                    logger.info(
                        '\nPublic card supports authenticated extended card. '
                        'Attempting to fetch from: '
                        f'{base_url}{EXTENDED_AGENT_CARD_PATH}'
                    )
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                    )
                    logger.info(
                        'Successfully fetched authenticated extended agent card:'
                    )
                    logger.info(
                        _extended_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card_to_use = (
                        _extended_card  # Update to use the extended card
                    )
                    logger.info(
                        '\nUsing AUTHENTICATED EXTENDED agent card for client '
                        'initialization.'
                    )
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,
                    )
            elif (
                _public_card
            ):  # supports_authenticated_extended_card is False or None
                logger.info(
                    '\nPublic card does not indicate support for an extended card. Using public card.'
                )

        except Exception as e:
            logger.error(
                f'Critical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                'Failed to fetch the public agent card. Cannot continue.'
            ) from e

        # --8<-- [start:send_message]
        client = A2AClient(
            httpx_client=httpx_client, 
            agent_card=final_agent_card_to_use
        )

        # First interaction - tell the agent something to remember
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': f'My favorite color is blue and I work as a software engineer. Context ID: {ctx_id}'}
                ],
                'message_id': uuid4().hex,
                'context_id': ctx_id,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        logger.info('\n=== First Message: Sharing personal info ===')
        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))
        
        # Extract context_id from first response for conversation continuity
        # Note: We don't reuse task_id since each task is completed and unique
        if hasattr(response.root, 'error') and response.root.error is not None:
            logger.error(f'Error from agent: {response.root.error}')
            raise RuntimeError(f'Agent returned error: {response.root.error}')
        
        context_id = response.root.result.context_id
        # --8<-- [end:send_message]

        # --8<-- [start:Multiturn]
        # Second interaction - ask about favorite color (tests memory)
        # Each message gets a new task_id, but shares the same context_id
        send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {
                        'kind': 'text',
                        'text': 'What is my favorite color?',
                    }
                ],
                'message_id': uuid4().hex,
                'context_id': context_id,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload_multiturn),
        )

        logger.info('\n=== Second Message: Testing memory recall ===')
        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        if hasattr(response.root, 'error') and response.root.error is not None:
            logger.error(f'Error from agent: {response.root.error}')
            raise RuntimeError(f'Agent returned error: {response.root.error}')

        # Update context_id from second response (should be the same, but verify)
        context_id = response.root.result.context_id

        # Third interaction - ask about profession (tests memory)
        # Again, new task but same context
        second_send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'What do I do for work?'}],
                'message_id': uuid4().hex,
                'context_id': context_id,
            },
        }

        second_request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**second_send_message_payload_multiturn),
        )

        logger.info('\n=== Third Message: Testing memory recall (profession) ===')
        second_response = await client.send_message(second_request)
        print(second_response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:Multiturn]

        # --8<-- [start:send_message_streaming]
        # Test streaming with a general question
        streaming_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Tell me a fun fact about Python programming.'}
                ],
                'message_id': uuid4().hex,
                'context_id': context_id,
            },
        }
        
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), 
            params=MessageSendParams(**streaming_message_payload)
        )

        logger.info('\n=== Streaming Message: General question ===')
        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:send_message_streaming]


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
