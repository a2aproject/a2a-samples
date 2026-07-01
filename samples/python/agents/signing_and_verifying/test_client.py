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


def _key_provider(kid: str, jku: str) -> PyJWK | str | bytes:
    """Fetch and parse public key from JKU URL given key ID (kid) and JKU URL."""
    if not kid or not jku:
        raise ValueError('Both key ID (kid) and JKU URL (jku) must be provided.')

    try:
        response = httpx.get(jku)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise ValueError(f'Failed to fetch public key from JKU URL ({jku}): {e}') from e

    try:
        keys = response.json()
    except ValueError as e:
        raise ValueError(f'Invalid JSON response from JKU URL ({jku}): {e}') from e

    if not isinstance(keys, dict):
        raise TypeError(f'Expected JSON object from JKU URL ({jku}), got {type(keys).__name__}.')

    pem_data_str = keys.get(kid)
    if not pem_data_str:
        raise ValueError(f'Key ID "{kid}" not found in JKU response from {jku}.')

    try:
        return serialization.load_pem_public_key(pem_data_str.encode('utf-8'))
    except Exception as e:
        raise ValueError(f'Failed to parse public key for kid "{kid}": {e}') from e


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
            # Pass verify_card_signature to validate the signature on the public Agent Card
            public_card = await resolver.get_agent_card(
                signature_verifier=verify_card_signature,
            )
            logger.info('Successfully fetched public agent card:')

        except Exception as e:
            logger.exception(
                'Critical error fetching public agent card.',
            )
            raise RuntimeError from e

        # Create Base Client directly via unified factory
        client = await create_client(
            agent=public_card,
            client_config=ClientConfig(streaming=False),
        )

        # Pass verify_card_signature to validate the signature on the extended Agent Card
        extended_card_with_signature = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest(),
            signature_verifier=verify_card_signature,
        )
        logger.info('Successfully fetched extended agent card with signature:')
        display_agent_card(extended_card_with_signature)
        logger.info('Signature:')
        logger.info(extended_card_with_signature.signatures)

        extended_card_without_signature = await client.get_extended_agent_card(
            GetExtendedAgentCardRequest()
        )
        logger.info('Successfully fetched extended agent card without signature:') #Signature is only for client-side verification purpose
        display_agent_card(extended_card_without_signature)


if __name__ == '__main__':
    asyncio.run(main())
