# Signing and Verifying Example (JS)

Signed agent used as an example for AgentCard signing and verifying in TypeScript.

Read more about signing and verifying AgentCards here: [Agent Card Signing](https://a2a-protocol.org/latest/specification/#84-agent-card-signing).

## Getting started

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the server:

   ```bash
   npm start
   ```

3. Run the test client (in a separate terminal):

   ```bash
   npm run client
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
