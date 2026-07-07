# Signing and Verifying Example

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

1. **Signing the Agent Card (Server-Side)**
   When the server receives a request for the agent card (either the public metadata or the authenticated extended version), it computes a signature of the card using the JSON Canonicalization Scheme (JCS) and signs it using JWS (JSON Web Signatures) with the private key. It attaches the signature block to the card, which contains a URL pointing to where the public key can be fetched.

2. **Fetching and Verifying the Card (Client-Side)**
   When the client connects to the agent, it first downloads the agent card. It reads the signature and key URL metadata from the card, fetches the public key from the key URL, and verifies that the signature matches the canonical card payload. 
   
   If the signature matches, the client trusts that the agent card is authentic. If the card was tampered with in transit or signed with a different key, the signature check fails.

   This flow is illustrated in the client's execution logs:
   
   ```text
   # 1. Client fetches the unsigned public card
   INFO:__main__:Attempting to fetch public agent card from: http://localhost:9999/.well-known/agent-card.json
   INFO:httpx:HTTP Request: GET http://localhost:9999/.well-known/agent-card.json "HTTP/1.1 200 OK"
   
   # 2. Client retrieves the public key matching the key ID in JWS header to verify the signature
   INFO:httpx:HTTP Request: GET http://localhost:9999/public_keys.json "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched public agent card:
   
   # 3. Client does the same for the extended card retrieved during authenticated request
   INFO:httpx:HTTP Request: GET http://localhost:9999/public_keys.json "HTTP/1.1 200 OK"
   INFO:__main__:Successfully fetched extended agent card with signature:
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
