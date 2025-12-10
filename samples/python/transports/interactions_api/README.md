# Interactions API Transport & Proxy

This directory contains a sample implementation of a custom **A2A Client Transport** that connects to the Gemini Interactions API, along with a local proxy server utility.

## Overview

There are two main components in this package:

1. **`InteractionsApiTransport`**: A custom Python class that implements the A2A `ClientTransport` interface. It acts as a bridge, translating A2A client requests into HTTP calls compatible with the Google Interactions API.
2. **Local Proxy Server**: A standalone utility that spins up a local HTTP server. This server accepts standard A2A JSON-RPC requests (e.g., from tools, GUIs, or other agents) and proxies them through the `InteractionsApiTransport` to the Interactions API.

## 1. InteractionsApiTransport

The `InteractionsApiTransport` class (`interactions_api_transport.py`) allows an A2A client to transparently communicate with the Interactions API.

**Note:** This is currently a sample implementation. To use this transport in your own application, you should copy the `interactions_api_transport.py` file directly into your project's source tree.

### Dependencies

To use the `InteractionsApiTransport` class, your project requires the following dependencies:

* `a2a-sdk`
* `httpx`
* `httpx-sse`

### Usage

To use the transport, you register it with your `ClientFactory` and configure an `AgentCard` to use it.

```python
from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from interactions_api_transport import InteractionsApiTransport

# 1. Setup the factory
client_config = ClientConfig()
client_factory = ClientFactory(client_config)
InteractionsApiTransport.setup(client_factory)

# 2. Create a card (or load one that uses the 'interactions-api' transport)
card = InteractionsApiTransport.make_card(
    url='https://generativelanguage.googleapis.com',
    model='deep-research-pro-preview-12-2025'
)

# 3. Create a client
client = client_factory.create(card)

# 4. Use the client as usual.
async for event in client.send_message(create_text_message_object('What is the weather like in Scandinavian countries?')):
    print(event)
```

## 2. Local Proxy Server

The local proxy server (`__main__.py`) is useful for testing and development. It allows you to expose the Interactions API as a standard A2A JSON-RPC endpoint.

This is particularly helpful if you want to connect off-the-shelf A2A tools, inspectors, or GUIs to the Interactions API without them needing native support for the custom `interactions-api` transport.

### Key Files

* `interactions_api_transport.py`: The core transport implementation.
* `__main__.py`: The entry point for the local proxy server.
* `request_handler.py`: Handles incoming JSON-RPC requests and forwards them to the transport.

### Running the Proxy

1. **Install Dependencies:**
    It is recommended to use `uv` for dependency management and running the project. If you don't have `uv` installed, please refer to the [official uv documentation](https://docs.astral.sh/uv/) for installation instructions.
    `uv run .` will automatically install necessary packages according to the `pyproject.toml` file.

2. **Set Environment Variables:**
    You need a valid API key. Create a `.env` file or export the variable:
    ```bash
    export GOOGLE_API_KEY="your_api_key_here"
    # OR
    export GEMINI_API_KEY="your_api_key_here"
    ```

3. **Start the Server:**
    Run the module to start the proxy using `uv`:
    ```bash
    uv run .
    ```

    By default, it listens on `localhost:10000` and proxies to the `deep-research-pro-preview-12-2025` model.

    **Options:**
    * `--host`: Host to bind to (default: `localhost`).
    * `--port`: Port to listen on (default: `10000`).
    * `--model`: The Interactions API model/agent to use (default: `deep-research-pro-preview-12-2025`). Other valid options are:
        * gemini-3-pro-preview
        * gemini-2.5-pro
        * gemini-2.5-flash
        * gemini-2.5-flash-lite
        * gemini-3-pro-image-preview
        * For the full list, see the Gemini Interactions API documentnation.

    ```bash
    uv run . --model another-model-name
    ```

4. **Connect a Client:**
    You can now connect any standard A2A client to `http://localhost:10000`. The proxy will handle the translation to the Interactions API.
