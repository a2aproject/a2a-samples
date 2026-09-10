# LangGraph Currency Agent with A2A Protocol

This sample demonstrates a currency conversion agent built with [LangGraph](https://langchain-ai.github.io/langgraph/) and exposed through the A2A protocol. It showcases conversational interactions with support for multi-turn dialogue and streaming responses.

## How It Works

This agent uses LangGraph with LLM (for example Google Gemini..) to provide currency exchange information through a ReAct agent pattern. The A2A protocol enables standardized interaction with the agent, allowing clients to send requests and receive real-time updates.

```mermaid
sequenceDiagram
    participant Client as A2A Client
    participant Server as A2A Server
    participant Agent as LangGraph Agent
    participant API as Frankfurter API

    Client->>Server: Send task with currency query
    Server->>Agent: Forward query to currency agent

    alt Complete Information
        Agent->>API: Call get_exchange_rate tool
        API->>Agent: Return exchange rate data
        Agent->>Server: Process data & return result
        Server->>Client: Respond with currency information
    else Incomplete Information
        Agent->>Server: Request additional input
        Server->>Client: Set state to TASK_STATE_INPUT_REQUIRED
        Client->>Server: Send additional information
        Server->>Agent: Forward additional info
        Agent->>API: Call get_exchange_rate tool
        API->>Agent: Return exchange rate data
        Agent->>Server: Process data & return result
        Server->>Client: Respond with currency information
    end

    alt With Streaming
        Note over Client,Server: Real-time status updates
        Server->>Client: "Looking up exchange rates..."
        Server->>Client: "Processing exchange rates..."
        Server->>Client: Final result
    end
```

## Key Features

- **Multi-turn Conversations**: Agent can request additional information when needed
- **Real-time Streaming**: Provides status updates during processing
- **Push Notifications**: Support for webhook-based notifications
- **Conversational Memory**: Maintains context across interactions
- **Currency Exchange Tool**: Integrates with Frankfurter API for real-time rates

## Prerequisites

- Python 3.12 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Setup & Running

1. Navigate to the samples directory:

   ```bash
   cd samples/python/agents/langgraph
   ```

2. Create an environment file with your API key:

   If you're using a Google Gemini model (gemini-2.0-flash, etc.):
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

   If you're using OpenAI or any compatible API (e.g., local LLM via Ollama, vLLM, LM Studio, etc.):
   ```bash
   echo "MODEL_SOURCE=openai" > .env
   echo "API_KEY=your_api_key_here" >> .env
   echo "TOOL_LLM_URL=your_llm_url" >> .env
   echo "TOOL_LLM_NAME=your_llm_name" >> .env
   ```

   > [!Tip]
   > For OpenAI-compatible models, ensure the model supports function calling / tool calling (e.g., standard chat models like `gpt-4o-mini`, `deepseek-chat`, `qwen2.5`). Reasoning/thinking models with forced tool restrictions are not recommended for tool execution.

3. Run the agent server:

   ```bash
   # Basic run on default port 10000
   uv run python -m app

   # On custom host/port
   uv run python -m app --host 0.0.0.0 --port 8080
   ```

4. In a separate terminal, run the test client:

   ```bash
   uv run python app/test_client.py
   ```

## Build Container Image

Agent can also be built using a container file.

1. Navigate to the `samples/python/agents/langgraph` directory:

  ```bash
  cd samples/python/agents/langgraph
  ```

2. Build the container file

    ```bash
    podman build . -t langgraph-a2a-server
    ```

> [!Tip]  
> Podman is a drop-in replacement for `docker` which can also be used in these commands.

3. Run your container

    ```bash
    podman run -p 10000:10000 -e GOOGLE_API_KEY=your_api_key_here langgraph-a2a-server
    ```

4. Run A2A client (follow step 5 from the section above)

> [!Important]
> * **Access URL:** You must access the A2A client through the URL `0.0.0.0:10000`. Using `localhost` will not work.
> * **Hostname Override:** If you're deploying to an environment where the hostname is defined differently outside the container, use the `HOST_OVERRIDE` environment variable to set the expected hostname on the Agent Card. This ensures proper communication with your client application.

## Technical Implementation

- **LangGraph ReAct Agent**: Uses the ReAct pattern for reasoning and tool usage
- **Streaming Support**: Provides incremental updates during processing
- **Checkpoint Memory**: Maintains conversation state between turns
- **Push Notification System**: Webhook-based updates with JWK authentication
- **A2A Protocol Integration**: Full compliance with A2A specifications

## Limitations

- Only supports text-based input/output (no multi-modal support)
- Uses Frankfurter API which has limited currency options
- Memory is session-based and not persisted between server restarts

## Examples

**Synchronous request**

Request:

```http
POST http://localhost:10000
Content-Type: application/json
A2A-Version: 1.0

{
    "id": "12113c25-b752-473f-977e-c9ad33cf4f56",
    "jsonrpc": "2.0",
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": "120ec73f93024993becf954d03a672bc",
            "role": "ROLE_USER",
            "parts": [
                {
                    "text": "how much is 10 USD in INR?"
                }
            ]
        }
    }
}
```

Response:

```json
{
    "id": "12113c25-b752-473f-977e-c9ad33cf4f56",
    "jsonrpc": "2.0",
    "result": {
        "task": {
            "id": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f",
            "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367",
            "status": {
                "state": "TASK_STATE_COMPLETED"
            },
            "artifacts": [
                {
                    "artifactId": "08373241-a745-4abe-a78b-9ca60882bcc6",
                    "name": "conversion_result",
                    "parts": [
                        {
                            "text": "10 USD is 856.2 INR."
                        }
                    ]
                }
            ],
            "history": [
                {
                    "messageId": "120ec73f93024993becf954d03a672bc",
                    "role": "ROLE_USER",
                    "parts": [
                        {
                            "text": "how much is 10 USD in INR?"
                        }
                    ],
                    "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f",
                    "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367"
                },
                {
                    "messageId": "d8b4d7de-709f-40f7-ae0c-fd6ee398a2bf",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Looking up the exchange rates..."
                        }
                    ],
                    "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f",
                    "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367"
                },
                {
                    "messageId": "ee0cb3b6-c3d6-4316-8d58-315c437a2a77",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Processing the exchange rates.."
                        }
                    ],
                    "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f",
                    "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367"
                }
            ]
        }
    }
}
```

**Multi-turn example**

Request - Seq 1:

```http
POST http://localhost:10000
Content-Type: application/json
A2A-Version: 1.0

{
    "id": "27be771b-708f-43b8-8366-968966d07ec0",
    "jsonrpc": "2.0",
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": "296eafc9233142bd98279e4055165f12",
            "role": "ROLE_USER",
            "parts": [
                {
                    "text": "How much is the exchange rate for 1 USD?"
                }
            ]
        }
    }
}
```

Response - Seq 2:

```json
{
    "id": "27be771b-708f-43b8-8366-968966d07ec0",
    "jsonrpc": "2.0",
    "result": {
        "task": {
            "id": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
            "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
            "status": {
                "state": "TASK_STATE_INPUT_REQUIRED",
                "message": {
                    "messageId": "f0f5f3ff-335c-4e77-9b4a-01ff3908e7be",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Please specify which currency you would like to convert to."
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                }
            },
            "history": [
                {
                    "messageId": "296eafc9233142bd98279e4055165f12",
                    "role": "ROLE_USER",
                    "parts": [
                        {
                            "text": "How much is the exchange rate for 1 USD?"
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                }
            ]
        }
    }
}
```

Request - Seq 3:

```http
POST http://localhost:10000
Content-Type: application/json
A2A-Version: 1.0

{
    "id": "b88d818d-1192-42be-b4eb-3ee6b96a7e35",
    "jsonrpc": "2.0",
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": "70371e1f231f4597b65ccdf534930ca9",
            "role": "ROLE_USER",
            "parts": [
                {
                    "text": "CAD"
                }
            ],
            "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
            "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
        }
    }
}
```

Response - Seq 4:

```json
{
    "id": "b88d818d-1192-42be-b4eb-3ee6b96a7e35",
    "jsonrpc": "2.0",
    "result": {
        "task": {
            "id": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
            "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
            "status": {
                "state": "TASK_STATE_COMPLETED"
            },
            "artifacts": [
                {
                    "artifactId": "08373241-a745-4abe-a78b-9ca60882bcc6",
                    "name": "conversion_result",
                    "parts": [
                        {
                            "text": "The exchange rate for 1 USD to CAD is 1.3739."
                        }
                    ]
                }
            ],
            "history": [
                {
                    "messageId": "296eafc9233142bd98279e4055165f12",
                    "role": "ROLE_USER",
                    "parts": [
                        {
                            "text": "How much is the exchange rate for 1 USD?"
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                },
                {
                    "messageId": "f0f5f3ff-335c-4e77-9b4a-01ff3908e7be",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Please specify which currency you would like to convert to."
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                },
                {
                    "messageId": "70371e1f231f4597b65ccdf534930ca9",
                    "role": "ROLE_USER",
                    "parts": [
                        {
                            "text": "CAD"
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                },
                {
                    "messageId": "0eb4f200-a8cd-4d34-94f8-4d223eb1b2c0",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Looking up the exchange rates..."
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                },
                {
                    "messageId": "41c7c03a-a772-4dc8-a868-e8c7b7defc91",
                    "role": "ROLE_AGENT",
                    "parts": [
                        {
                            "text": "Processing the exchange rates.."
                        }
                    ],
                    "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
                    "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101"
                }
            ]
        }
    }
}
```

**Streaming example**

Request:

```http
POST http://localhost:10000
Content-Type: application/json
A2A-Version: 1.0

{
    "id": "6d12d159-ec67-46e6-8d43-18480ce7f6ca",
    "jsonrpc": "2.0",
    "method": "SendStreamingMessage",
    "params": {
        "message": {
            "messageId": "2f9538ef0984471aa0d5179ce3c67a28",
            "role": "ROLE_USER",
            "parts": [
                {
                    "text": "how much is 10 USD in INR?"
                }
            ]
        }
    }
}
```

Response:

```http
data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"task":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","history":[{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","messageId":"2f9538ef0984471aa0d5179ce3c67a28","parts":[{"text":"how much is 10 USD in INR?"}],"role":"ROLE_USER","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}],"id":"423a2569-f272-4d75-a4d1-cdc6682188e5","status":{"state":"TASK_STATE_SUBMITTED"}}}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"statusUpdate":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","status":{"message":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","messageId":"1854a825-c64f-4f30-96f2-c8aa558b83f9","parts":[{"text":"Looking up the exchange rates..."}],"role":"ROLE_AGENT","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"},"state":"TASK_STATE_WORKING"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"statusUpdate":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","status":{"message":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","messageId":"e72127a6-4830-4320-bf23-235ac79b9a13","parts":[{"text":"Processing the exchange rates.."}],"role":"ROLE_AGENT","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"},"state":"TASK_STATE_WORKING"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"artifactUpdate":{"artifact":{"artifactId":"08373241-a745-4abe-a78b-9ca60882bcc6","name":"conversion_result","parts":[{"text":"10 USD is 856.2 INR."}]},"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"statusUpdate":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","status":{"state":"TASK_STATE_COMPLETED"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}}
```

## Learn More

- [A2A Protocol Documentation](https://a2a-protocol.org/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Frankfurter API](https://www.frankfurter.app/docs/)
- [Google Gemini API](https://ai.google.dev/gemini-api)


## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics
of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to
treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages,
artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent
could provide an AgentCard containing crafted data in its fields (e.g., description, name,
skills.description). If this data is used without sanitization to construct prompts for a Large
Language Model (LLM), it could expose your application to prompt injection attacks. Failure to
properly validate and sanitize this data before use can introduce security vulnerabilities into
your application.

Developers are responsible for implementing appropriate security measures, such as input validation
and secure handling of credentials to protect their systems and users.
