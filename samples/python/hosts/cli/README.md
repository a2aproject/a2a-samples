## Command-Line Interface (CLI) Host
The CLI is a host application that demonstrates the capabilities of the A2A Python Client SDK. It allows you to interact with any A2A-compliant agent directly from your terminal.

## Key Features:

Reads an agent's AgentCard to understand its capabilities.

Supports text-based, interactive conversations with a remote agent.

Automatically uses streaming for real-time updates if the agent supports it.

Handles authenticated agents using bearer tokens.

Pretty-prints server responses for improved readability.

Allows attaching local files to messages.

## Prerequisites
Python 3.12 or higher

UV (recommended) or pip

A running A2A-compliant agent server


## Running the CLI

1. Navigate to the CLI sample directory:
    ```bash
    cd samples/python/hosts/cli
    ```
2. Run the example client
    ```
    uv run . --agent [url-of-your-a2a-server]
    ```

   for example `--agent http://localhost:10000`. More command line options are documented in the source code. 


For example:

uv run . --agent http://localhost:10000

Note: You can run the calendar_agent sample and use it's URL to test OAuth functionality.

## Authentication
The CLI supports interacting with agents that require authentication via bearer tokens (as is common with OAuth2 or OpenID Connect).

### Using Google Cloud Authentication
If your agent uses Google's Identity-Aware Proxy (IAP) or another service that accepts Google-issued ID tokens, you can use the --gcloud-auth flag. This will automatically use the gcloud CLI to fetch a token and send it with every request.

Example:

# Ensure you are logged in with gcloud first: gcloud auth login
uv run . --agent <your-agent-url> --gcloud-auth

Command-line Options
--agent <URL>: (Required) The base URL of the A2A agent you want to interact with.

--session <ID>: A numeric ID used to maintain a persistent client-side session for credential management. If you run the CLI with the same session ID, it will reuse the same authentication credentials. If not provided, a new random session is created each time.

--gcloud-auth: A flag to enable automatic authentication using an identity token from the gcloud CLI.

--history: A flag to display the full task history after a task completes.

--use_push_notifications: A flag to enable testing with push notifications. Requires a running push notification receiver.

--push_notification_receiver <URL>: The URL of the push notification receiver service. Defaults to http://localhost:5000.
