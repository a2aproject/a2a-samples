import * as crypto from 'node:crypto';

import {
  AGENT_CARD_PATH,
  AgentCard,
  verifyAgentCardSignature,
} from '@a2a-js/sdk';
import { ClientFactory, DefaultAgentCardResolver } from '@a2a-js/sdk/client';

async function keyProvider(kid: string, jku?: string): Promise<crypto.KeyObject> {
  /** Fetch and parse public key from JKU URL given key ID (kid) and JKU URL. */
  if (typeof kid !== 'string' || !kid) {
    throw new TypeError(`Expected kid: string, but got: ${typeof kid} (${kid})`);
  }
  if (typeof jku !== 'string' || !jku) {
    throw new TypeError(`Expected jku: string, but got: ${typeof jku} (${jku})`);
  }

  let response: Response;
  try {
    response = await fetch(jku);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }
  } catch (err) {
    throw new Error(`Failed to fetch public key from JKU URL (${jku}): ${err}`);
  }

  const keys = (await response.json()) as Record<string, string>;
  const pemDataStr = keys[kid];

  if (!pemDataStr) {
    throw new Error('Invalid JWK Key ID.');
  }

  return crypto.createPublicKey(pemDataStr);
}

// Create a verifier function to validate AgentCard JWS signatures
const verifyCardSignature = verifyAgentCardSignature(keyProvider);

async function main(): Promise<void> {
  /** Main function. */

  const baseUrl = 'http://localhost:9999';

  // Initialize AgentCardResolver
  const resolver = new DefaultAgentCardResolver();

  let publicCard: AgentCard;
  try {
    console.log(
      `Attempting to fetch public agent card from: ${baseUrl}${AGENT_CARD_PATH}`
    );
    publicCard = await resolver.resolve(baseUrl);

    // Pass verifyCardSignature to validate the signature on the public Agent Card
    await verifyCardSignature(publicCard);
    console.log('Successfully fetched public agent card:');
  } catch (e) {
    console.error('Critical error fetching public agent card:', e);
    throw e;
  }

  // Create Client directly via ClientFactory
  const clientFactory = new ClientFactory();
  const client = await clientFactory.createFromAgentCard(publicCard);

  // Pass verifyCardSignature to validate the signature on the extended Agent Card
  const extendedCardWithSignature = await client.getAgentCard(
    undefined,
    verifyCardSignature
  );

  console.log('Successfully fetched extended agent card with signature:');
  console.log(JSON.stringify(extendedCardWithSignature, null, 2));
  console.log('Signature:');
  console.log(JSON.stringify(extendedCardWithSignature.signatures, null, 2));

  const extendedCardWithoutSignature = await client.getAgentCard();
  console.log('Successfully fetched extended agent card without signature:');
  console.log(JSON.stringify(extendedCardWithoutSignature, null, 2));
}

main().catch((err) => {
  console.error('Error in main:', err);
  process.exit(1);
});
