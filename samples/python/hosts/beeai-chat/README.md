# BeeAI Framework A2A Chat Client

This sample demonstrates how to create a chat client using the [BeeAI Framework](https://docs.beeai.dev/introduction/welcome) that communicates with A2A agents. This provides a simple terminal-based interface to interact with your AI agents.

## Prerequisites

- Python 3.10 or higher
- [BeeAI Chat agent](../../agents/beeai-chat/README.md) running

## Run the Sample

1. Navigate to the samples directory:

    ```bash
    cd samples/python/hosts/beeai-chat
    ```

2. Create venv and install Requirements

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install .
    ```

3. Run the chat client:

    ```bash
    python __main__.py
    ```

## Run using Docker

```sh
docker build -t beeai_chat_client .
docker run -it --network host beeai_chat_client
```
