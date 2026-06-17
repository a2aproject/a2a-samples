# A2A CLI

The CLI is a small host application that demonstrates the capabilities of an `A2AClient`. It supports reading a server's `AgentCard` and text-based collaboration with a remote agent. All content received from the A2A server is printed to the console.

This module contains two versions of the CLI, targeting different A2A SDK versions:

| Directory | SDK Version | Description |
|-----------|-------------|-------------|
| [cli_03](cli_03/) | `a2a-sdk >= 0.3.0` | Uses Pydantic models, JSON-RPC |
| [cli_v10](cli_v10/) | `a2a-sdk >= 1.0.0` | Uses Protobuf messages, unified streaming |

See each subdirectory's README for detailed usage and migration notes.

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
