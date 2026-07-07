# Signing and Verifying Example (Go)

This sample demonstrates how to sign an **Agent Card** on the server side and verify its signature on the client side to establish and validate the agent's identity.

Read more about signing and verifying AgentCards here: [Agent Card Signing](https://a2a-protocol.org/latest/specification/#84-agent-card-signing).

> [!IMPORTANT]
> This sample is about validating the authenticity of the **Agent Card** itself (metadata and capabilities) during discovery. It is **not** about authenticating user requests or verifying client identities for agent interactions.

## Getting started

You can run both the server and the test client together in one terminal:

```bash
go run . -client
```

---

## How it works

The agent's publisher generates a cryptographic public/private key pair. The private key remains secure on the server, while the public key is exposed via a public URL endpoint.

The agent publishes two cards:
* **Public Agent Card:** Accessible to anyone. It contains basic metadata and general skills of the agent.
* **Extended Agent Card:** Accessible only after the client performs an authorized handshake. It contains additional, restricted skills.

1. **Signing the Agent Cards (Server-Side)**
   When the server starts up, it generates the keys, signs both cards using JWS (JSON Web Signatures) with the private key, and saves the public key to `public_keys.json`. When a client requests either card, the server serves the signed card containing a Key ID (`kid`) and a public key URL (`jku`).

2. **Fetching and Verifying the Cards (Client-Side)**
   When the client connects to the agent, it first downloads the public card, and later requests the extended card. For both cards, the client can choose to resolve them in two ways:
   * **Unverified:** The client fetches the card and uses it directly. No signature checking is performed.
   * **Verified:** The client instructs the resolver or client to verify the card's signature. The signature metadata is parsed, the publisher's public key is downloaded from the URL (`jku`) listed in the signature, and the cryptographic signature is verified against the canonicalized card payload.

   This flow is illustrated in the client's execution logs:

   ```text
   # 1. Fetching the public card WITHOUT signature verification (No public keys are fetched)
   2026/07/07 14:05:15 Attempting to fetch public agent card from: http://localhost:9999/.well-known/agent-card.json
   2026/07/07 14:05:15 Successfully fetched public agent card without verification.

   # 2. Fetching the public card WITH signature verification (Public keys are fetched and verified)
   2026/07/07 14:05:15 Successfully fetched public agent card with verification:
   2026/07/07 14:05:15 {"name":"Signed Agent","description":"Public card containing basic skills of the signed agent.", ...}

   # 3. Fetching the extended card WITHOUT signature verification (No public keys are fetched)
   2026/07/07 14:05:15 Successfully fetched extended agent card without verification:
   2026/07/07 14:05:15 {"name":"Signed Agent - Extended Card","description":"Extended card containing additional capabilities of the signed agent.", ...}

   # 4. Fetching the extended card WITH signature verification (Public keys are fetched and verified)
   2026/07/07 14:05:16 Successfully fetched extended agent card with verification:
   2026/07/07 14:05:16 {"name":"Signed Agent - Extended Card","description":"Extended card containing additional capabilities of the signed agent.", ...}
   ```

## Disclaimer
Important: The sample code provided is for demonstration purposes
and illustrates the mechanics of the Agent-to-Agent (A2A) protocol.
When building production applications, it is critical to treat any agent
operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard,
messages, artifacts, and task statuses—should be handled as untrusted input.
For example, a malicious agent could provide an AgentCard containing crafted data
in its fields (e.g., description, name, skills.description). If this data is used
without sanitization to construct prompts for a Large Language Model (LLM),
it could expose your application to prompt injection attacks. Failure to properly
validate and sanitize this data before use can introduce security vulnerabilities
into your application.

Developers are responsible for implementing appropriate security measures,
such as input validation and secure handling of credentials to protect their systems and users.
