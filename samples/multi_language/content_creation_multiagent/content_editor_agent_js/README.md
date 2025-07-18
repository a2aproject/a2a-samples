# JavaScript Sample

The provided sample is built using [Genkit](https://genkit.dev/) using the Gemini API.

## Agents

- [Content Editor Agent](src/agents/content-editor-agent/README.md): An agent that can proof-read and polish content.

## Testing the Agent

First, follow the instructions in the agent's README file, then run `npx tsx ./cli.ts` to start up a command-line client to talk to the agents. Example:

1. Navigate to the `content_editor_agent_js` directory:
    ```bash
    cd samples/multi_language/content_creation_multiagent/content_editor_agent_js
    ```
   
2. Create an environment file with your API key:
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

3. Run npm install:
    ```bash
    npm install
    ```

4. Run an agent:
```bash
npm run agents:content-editor-agent-js

# in a separate terminal
npm run a2a:cli
```
---
**NOTE:** 
This is sample code and not production-quality libraries.
---

## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.