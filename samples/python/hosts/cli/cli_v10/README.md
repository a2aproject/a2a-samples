# A2A CLI (1.0.0)

The CLI is a small host application that demonstrates the capabilities of an A2A 1.0.0 `Client`. It supports reading a server's `AgentCard` and text-based collaboration with a remote agent. All content received from the A2A server is printed to the console.

The client will use streaming if the server supports it.

## Prerequisites

- Python 3.13 or higher
- UV
- A running A2A 1.0.0 server

## Running the CLI

1. Navigate to the CLI v1 sample directory:

    ```bash
    cd samples/python/hosts/cli/cli_v10
    ```

2. Run the example client

    ```sh
    uv run . --agent [url-of-your-a2a-server]
    ```

   for example `--agent http://localhost:8083`. More command line options are documented in the source code.

### Options

- `--agent URL` - A2A server URL (default: `http://localhost:8083`)
- `--bearer-token TOKEN` - Bearer token for authentication (or set `A2A_CLI_BEARER_TOKEN` env var)
- `--session ID` - Session/context ID (default: generates a new one)
- `--history` - Retrieve task history after each interaction
- `--use_push_notifications` - Enable push notification listener
- `--push_notification_receiver URL` - Push notification receiver URL (default: `http://localhost:5000`)
- `--header KEY=VALUE` - Extra headers to send (repeatable)
- `--enabled_extensions URIS` - Comma-separated list of extension URIs to enable

## Migration from v0.3

Key differences from the v0.3 CLI (`../cli_03`):

| Area | v0.3 (parent dir) | v1.0 (this dir) |
|------|---------|---------|
| Types | Pydantic models | Protobuf messages |
| Client | `A2AClient(httpx_client, agent_card)` | `create_client(card, client_config)` |
| Messaging | `TextPart`, `FilePart(FileWithBytes)` | `new_text_part()`, `new_raw_part(bytes)` |
| Streaming | `send_message()` / `send_message_streaming()` | Unified `send_message()` → `AsyncIterator[StreamResponse]` |
| Responses | JSON-RPC unwrapping, `isinstance()` | `response.HasField('task'\|'message'\|...)` |
| Errors | `JSONRPCErrorResponse` | `A2AClientError` exceptions |
| Task state | `TaskState.input_required` | `TaskState.TASK_STATE_INPUT_REQUIRED` |
| Auth/Headers | httpx headers dict | `ClientCallContext(service_parameters=...)` |
| Serialization | `model_dump_json()` | `MessageToJson()` |

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
