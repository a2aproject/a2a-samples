# Real-Estate Agent (A2A) Sample

![Real Estate Agent Banner](assets/a2a-real-estate-agent-banner.png)

This sample demonstrates a sophisticated real-estate agent based on the Agent-to-Agent (A2A) protocol. The agent is capable of understanding natural language queries, performing filtered searches for rental properties, and returning structured results.

## 🔗 Original Source and Contributions

This sample is a snapshot of an active open-source project. For the latest updates, to report issues, or to contribute, please visit the original repositories:

*   **Real-Estate Agent:** `https://github.com/amineremache/robolancerai-real-estate-agent`
*   **Dafty MCP Server:** `https://github.com/amineremache/dafty-mcp`

We encourage you to contribute directly to the source projects!

## 🏛️ Architecture

The system is composed of three main services orchestrated with `docker-compose`:

1.  **`real-estate-agent`**: The core Python A2A agent that handles user requests and orchestrates tool calls.
2.  **`dafty-mcp`**: A Node.js/TypeScript MCP (Model Context Protocol) tool server that provides the tools for interacting with the Daft.ie rental service. It includes a web scraper and an intelligent query parser.
3.  **`ollama`**: A local LLM service that runs the `tinydolphin` model to parse natural language queries into structured JSON.

## ✨ Features

-   **Natural Language Understanding**: Uses a local LLM to parse user queries like "Find a 2-bed apartment in Dublin under €2000."
-   **Filtered Search**: Performs filtered searches based on location, price, and number of bedrooms.
-   **Self-Contained Environment**: The entire application runs in a portable and isolated Docker environment.
-   **A2A Compliant**: Built on the A2A protocol for standardized agent communication.

## 🚀 Getting Started

### Prerequisites

-   Docker and `docker-compose` must be installed.
-   You must have a `.env` file in the root of this sample directory. You can create one from the `.env.example` file and add your `API_KEY`.

### Installation and Running

1.  **Navigate to the sample directory:**
    ```bash
    cd samples/python/agents/real_estate_agent
    ```

2.  **Build and start the services:**
    ```bash
    docker-compose up --build
    ```

3.  **The services will now be running:**
    *   The `real-estate-agent` will be available on port `3001`.
    *   The `dafty-mcp` and `ollama` services will be running in the background.

## 🧪 Testing the Agent

You can send a request to the agent using `curl`. The following example demonstrates how to search for a 2-bedroom apartment in Dublin for under €2000.

```bash
curl -X POST http://localhost:3001/ \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <YOUR_API_KEY>" \
-d '{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "1",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Find a 2-bed apartment in Dublin under €2000."
        }
      ]
    }
  }
}' > results.json
```

The results of the query will be saved to a `results.json` file in your project directory.