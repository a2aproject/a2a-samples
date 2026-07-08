# Sign and Verify Agent Card Example

This sample demonstrates how to sign an **Agent Card** on the server side and verify its signature on the client side to establish and validate the agent's identity.

Read more about signing and verifying AgentCards here: [Agent Card Signing](https://a2a-protocol.org/latest/specification/#84-agent-card-signing).

> [!IMPORTANT]
> This sample is about validating the authenticity of the **Agent Card** itself (metadata and capabilities) during discovery. It is **not** about authenticating user requests or verifying client identities for agent interactions.

## Getting started

1. Setup the virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the server:

   ```bash
   python3 __main__.py
   ```

3. Run the test client:

   ```bash
   python3 test_client.py
   ```

## How it works

The agent's publisher generates a cryptographic public/private key pair. The private key remains secure on the server, while the public key is exposed via a public URL endpoint.

The agent publishes two cards:
* **Public Agent Card:** Accessible to anyone. It contains basic metadata and general skills of the agent.
* **Extended Agent Card:** Accessible only after the client performs an authorized handshake. It contains additional, restricted skills.

1. **Signing the Agent Cards (Server-Side)**
   When the server receives a request for the agent card (either the public metadata or the extended version), it computes a signature of the card using the JSON Canonicalization Scheme (JCS) and signs it using JWS (JSON Web Signatures) with the private key. It attaches the signature block containing a Key ID (`kid`) and public key URL (`jku`) to the returned card.

2. **Fetching and Verifying the Cards (Client-Side)**
   When the client connects to the agent, it first downloads the public card, and later requests the extended card. For both cards, the client can choose to resolve them in two ways:
   * **Unverified:** The client fetches the card and uses it directly. No signature checking is performed.
   * **Verified:** The client instructs the resolver or client to verify the card's signature. The signature metadata is parsed, the publisher's public key is downloaded from the URL (`jku`) listed in the signature, and the cryptographic signature is verified against the canonicalized card payload.

   This flow is illustrated in the client's execution logs:

   ```text
   # 1. Fetching the public card WITHOUT signature verification (No public keys are fetched)
   INFO:__main__:Attempting to fetch public agent card from: http://localhost:9999/.well-known/agent-card.json
   INFO:httpx:HTTP Request: GET http://localhost:9999/.well-known/agent-card.json "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched public agent card without verification.

   # 2. Fetching the public card WITH signature verification (Public keys are fetched and verified)
   INFO:httpx:HTTP Request: GET http://localhost:9999/.well-known/agent-card.json "HTTP/1.1 200 OK"
   INFO:httpx:HTTP Request: GET http://localhost:9999/public_keys.json "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched public agent card with verification:

   # 3. Fetching the extended card WITHOUT signature verification (No public keys are fetched)
   INFO:httpx:HTTP Request: POST http://localhost:9999 "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched extended agent card without verification:

   # 4. Fetching the extended card WITH signature verification (Public keys are fetched and verified)
   INFO:httpx:HTTP Request: POST http://localhost:9999 "HTTP/1.1 200 OK"
   INFO:httpx:HTTP Request: GET http://localhost:9999/public_keys.json "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched extended agent card with verification:
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
