import json
import logging

import httpx

from a2a.client import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    TextPart,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from a2a.utils.signing import create_signature_verifier
from cryptography.hazmat.primitives import serialization
from jwt.api_jwk import PyJWK


def _key_provider(kid: str | None, jku: str | None) -> PyJWK | str | bytes:
    if not kid or not jku:
        raise ValueError('kid and jku must be provided')

    try:
        with open(jku) as f:
            keys = json.load(f)
    except FileNotFoundError:
        raise ValueError(f'JKU file not found: {jku}')
    except json.JSONDecodeError as e:
        logging.warning(f'Invalid JSON in {jku}', exc_info=True)
        raise ValueError(f'Invalid JSON in {jku}') from e

    pem_data_str = keys.get(kid)
    if pem_data_str:
        pem_data = pem_data_str.encode('utf-8')
        try:
            public_key = serialization.load_pem_public_key(pem_data)
            return public_key
        except Exception as e:
            logging.exception(f"Error loading PEM key for kid '{kid}'")
            raise ValueError(f"Error loading PEM key for kid '{kid}'") from e
    else:
        raise ValueError(f"Key with kid '{kid}' not found in '{jku}'")


signature_verifier = create_signature_verifier(_key_provider, ['ES256'])


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
            # agent_card_path uses default, extended_agent_card_path also uses default
        )
        # --8<-- [end:A2ACardResolver]

        # Fetch Public Agent Card and Initialize BaseClient
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
            )
            _public_card = await resolver.get_agent_card(
                signature_verifier=signature_verifier,
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
                        f'\nPublic card supports authenticated extended card. Attempting to fetch from: {base_url}{EXTENDED_AGENT_CARD_PATH}'
                    )
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                        signature_verifier=signature_verifier,
                    )  # add signature verifier
                    logger.info(
                        'Successfully fetched AND VERIFIED authenticated extended agent card:'
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
                        '\nUsing AUTHENTICATED EXTENDED agent card for client initialization.'
                    )
                except Exception as e_extended:
                    logger.warning(
                        f'Failed to fetch or verify extended agent card: {e_extended}. Will proceed with public card.',
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

        # Create Client Factory
        client_factory = ClientFactory(config=ClientConfig(streaming=False))

        # Create Base Client
        client = client_factory.create(final_agent_card_to_use)

        # --8<-- [start:send_message]
        message_to_send = Message(
            role=Role.user,
            message_id='msg-integration-test-signing-and-verifying',
            parts=[
                Part(root=TextPart(text='Hello, signature verification test!'))
            ],
        )

        print('send_message response:')
        async for chunk in client.send_message(message_to_send):
            chunk_dict = chunk.model_dump(mode='json', exclude_none=True)
            parts = chunk_dict['parts']
            for part in parts:
                print(part['text'])
        # --8<-- [end:send_message]

        # --8<-- [start:get_card]
        get_card_response = await client.get_card(
            signature_verifier=signature_verifier
        )
        print('fetched again:')
        print(get_card_response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:get_card]


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
