import asyncio
import logging

import httpx

from a2a.client import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types.a2a_pb2 import GetExtendedAgentCardRequest
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)
from a2a.utils.signing import create_signature_verifier
from cryptography.hazmat.primitives import serialization
from jwt.api_jwk import PyJWK


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
            logger.info(public_card)
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

        except Exception as e:
            logger.exception(
                'Critical error fetching public agent card.',
            )
            raise RuntimeError from e

        # Create Client Factory
        client_factory = ClientFactory(config=ClientConfig(streaming=False))

        # Create Base Client
        client = client_factory.create(public_card)

        get_card_response = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest(), signature_verifier=signature_verifier
        )  # Verifies the AgentCard using signature_verifier function before returning it
        print('Fetched extended card:')
        print(get_card_response)


if __name__ == '__main__':
    asyncio.run(main())
