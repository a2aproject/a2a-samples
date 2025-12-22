import logging

from typing import TYPE_CHECKING

import httpx

from a2a.client import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from a2a.utils.signing import create_signature_verifier
from cryptography.hazmat.primitives import serialization
from jwt.api_jwk import PyJWK


if TYPE_CHECKING:
    from a2a.types import AgentCard


def _key_provider(kid: str | None, jku: str | None) -> PyJWK | str | bytes:
    if not kid or not jku:
        print('kid or jku missing')
        raise ValueError

    response = httpx.get(jku)
    keys = response.json()

    pem_data_str = keys.get(kid)
    if pem_data_str:
        pem_data = pem_data_str.encode('utf-8')
        return serialization.load_pem_public_key(pem_data)
    raise ValueError


signature_verifier = create_signature_verifier(_key_provider, ['ES256'])


async def main() -> None:
    """Main function."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:9999'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        # Fetch and verify Agent Card and initialize BaseClient
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                'Attempting to fetch public agent card from: %s%s',
                base_url,
                AGENT_CARD_WELL_KNOWN_PATH,
            )
            public_card = await resolver.get_agent_card(
                signature_verifier=signature_verifier,
            )  # Verifies the AgentCard using signature_verifier function before returning it
            logger.info('Successfully fetched public agent card:')
            logger.info(
                public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = public_card
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

            if public_card.supports_authenticated_extended_card:
                try:
                    logger.info(
                        '\nPublic card supports authenticated extended card. Attempting to fetch from: %s%s',
                        base_url,
                        EXTENDED_AGENT_CARD_PATH,
                    )
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                        signature_verifier=signature_verifier,
                    )  # Verifies the extended AgentCard using signature_verifier function before returning it
                    logger.info(
                        'Successfully fetched and verified authenticated extended agent card:'
                    )
                    logger.info(
                        extended_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card_to_use = extended_card
                    logger.info(
                        '\nUsing AUTHENTICATED EXTENDED agent card for client initialization.'
                    )
                except (httpx.HTTPError, ValueError) as e_extended:
                    logger.warning(
                        'Failed to fetch or verify extended agent card: %s. Will proceed with public card.',
                        e_extended,
                        exc_info=True,
                    )
            elif public_card:
                logger.info(
                    '\nPublic card does not indicate support for an extended card. Using public card.'
                )

        except Exception as e:
            logger.exception(
                'Critical error fetching public agent card.',
            )
            raise RuntimeError from e

        # Create Client Factory
        client_factory = ClientFactory(config=ClientConfig(streaming=False))

        # Create Base Client
        client = client_factory.create(final_agent_card_to_use)

        get_card_response = await client.get_card(
            signature_verifier=signature_verifier
        )  # Verifies the AgentCard using signature_verifier function before returning it
        print('fetched again:')
        print(get_card_response.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
