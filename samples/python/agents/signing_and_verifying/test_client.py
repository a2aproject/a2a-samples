import asyncio
import logging

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import display_agent_card
from a2a.types import GetExtendedAgentCardRequest
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)
from a2a.utils.signing import create_signature_verifier
from cryptography.hazmat.primitives import serialization
from jwt.api_jwk import PyJWK


def _key_provider(key_id: str, jku: str) -> PyJWK | str | bytes:
    """Fetch and parse public key from JKU URL given key ID (key_id) and JKU URL."""
    if not isinstance(key_id, str) or not key_id:
        raise TypeError(f'Expected key_id: str, but got: {type(key_id).__name__} ({key_id!r})')
    if not isinstance(jku, str) or not jku:
        raise TypeError(f'Expected jku: str, but got: {type(jku).__name__} ({jku!r})')

    try:
        response = httpx.get(jku)
        response.raise_for_status()
    except httpx.HTTPError as err:
        raise ValueError(f'Failed to fetch public key from JKU URL ({jku}): {err}') from err

    keys = response.json()
    pem_data_str = keys.get(key_id)

    if not pem_data_str:
        raise ValueError('Invalid JWK Key ID.')

    return serialization.load_pem_public_key(pem_data_str.encode('utf-8'))


# Create a verifier function to validate AgentCard JWS signatures
verify_card_signature = create_signature_verifier(_key_provider, ['ES256'])


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
            # 1. Fetch public agent card without verifying signature
            _ = await resolver.get_agent_card()
            logger.info('Successfully fetched public agent card without verification.')

            # 2. Fetch public agent card and verify signature
            public_card_verified = await resolver.get_agent_card(
                signature_verifier=verify_card_signature,
            )
            logger.info('Successfully fetched public agent card with verification:')
            display_agent_card(public_card_verified)

        except Exception as e:
            logger.exception(
                'Critical error fetching public agent card.',
            )
            raise RuntimeError from e

        # Create Base Client directly via unified factory
        client = await create_client(
            agent=public_card_verified,
            client_config=ClientConfig(streaming=False),
        )

        # 3. Fetch extended agent card without signature verification
        extended_card_unverified = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest()
        )
        logger.info('Successfully fetched extended agent card without verification:')
        display_agent_card(extended_card_unverified)

        # 4. Fetch extended agent card and verify signature
        extended_card_verified = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest(),
            signature_verifier=verify_card_signature,
        )
        logger.info('Successfully fetched extended agent card with verification:')
        display_agent_card(extended_card_verified)

        await client.close()


if __name__ == '__main__':
    asyncio.run(main())
