/* eslint-disable n/no-missing-import */
/* eslint-disable n/no-unsupported-features/node-builtins */
/* eslint-disable n/no-process-exit */
import * as crypto from "node:crypto";

import {
    AGENT_CARD_PATH,
    AgentCard,
    verifyAgentCardSignature,
} from "@a2a-js/sdk";
import { ClientFactory, DefaultAgentCardResolver } from "@a2a-js/sdk/client";

async function keyProvider(
    keyId: string,
    jku?: string
): Promise<crypto.KeyObject> {
    /** Fetch and parse public key from JKU URL given key ID (keyId) and JKU URL. */
    if (typeof keyId !== "string" || !keyId) {
        throw new TypeError(
            `Expected keyId: string, but got: ${typeof keyId} (${keyId})`
        );
    }
    if (typeof jku !== "string" || !jku) {
        throw new TypeError(
            `Expected jku: string, but got: ${typeof jku} (${jku})`
        );
    }

    let response: Response;
    try {
        response = await fetch(jku);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} ${response.statusText}`);
        }
    } catch (err) {
        throw new Error(
            `Failed to fetch public key from JKU URL (${jku}): ${err}`
        );
    }

    const keys = (await response.json()) as Record<string, string>;
    const pemDataStr = keys[keyId];

    if (!pemDataStr) {
        throw new Error("Invalid JWK Key ID.");
    }

    return crypto.createPublicKey(pemDataStr);
}

// Create a verifier function to validate AgentCard JWS signatures
const verifyCardSignature = verifyAgentCardSignature(keyProvider);

async function main(): Promise<void> {
    const baseUrl = "http://localhost:9999";

    // Initialize AgentCardResolver
    const resolver = new DefaultAgentCardResolver();

    console.log(
        `Attempting to fetch public agent card from: ${baseUrl}${AGENT_CARD_PATH}`
    );

    // 1. Fetch public agent card without verifying signature
    try {
        await resolver.resolve(baseUrl);
        console.log(
            "Successfully fetched public agent card without verification."
        );
    } catch (e) {
        console.error("Critical error fetching public agent card:", e);
        throw e;
    }

    // 2. Fetch public agent card and verify signature
    let publicCardVerified: AgentCard;
    try {
        publicCardVerified = await resolver.resolve(baseUrl);
        await verifyCardSignature(publicCardVerified);
        console.log(
            "Successfully fetched public agent card with verification:"
        );
        console.log(JSON.stringify(publicCardVerified, null, 2));
    } catch (e) {
        console.error("Critical error fetching public agent card:", e);
        throw e;
    }

    // Create Client directly via ClientFactory
    const clientFactory = new ClientFactory();
    const client = await clientFactory.createFromAgentCard(publicCardVerified);

    // 3. Fetch extended agent card without signature verification
    const extendedCardUnverified = await client.getAgentCard();
    console.log(
        "Successfully fetched extended agent card without verification:"
    );
    console.log(JSON.stringify(extendedCardUnverified, null, 2));

    // 4. Fetch extended agent card and verify signature
    const extendedCardVerified = await client.getAgentCard(
        undefined,
        verifyCardSignature
    );
    console.log("Successfully fetched extended agent card with verification:");
    console.log(JSON.stringify(extendedCardVerified, null, 2));
}

main().catch((err) => {
    console.error("Error in main:", err);
    process.exit(1);
});
