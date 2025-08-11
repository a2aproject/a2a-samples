# BeeAI Framework A2A Chat Agent

This sample demonstrates how to create a chat agent using the [BeeAI Framework](https://docs.beeai.dev/introduction/welcome) with Agent2Agent (A2A) communication protocol. This agent has access to web search and weather tools.

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/) installed and running

## Run the Sample

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/beeai-chat
    ```

2. Create venv and install Requirements

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install .
    ```

3. Pull the model to the ollama:

   ```bash
   ollama pull granite3.3:8b
   ```

4. Run the A2A agent:

    ```bash
    python __main__.py
    ```

5. Run the [BeeAI Chat client](../../hosts/beeai-chat/README.md)

## Run using Docker

```sh
docker build -t beeai_chat_agent .
docker run -p 9999:9999 -e OLLAMA_API_BASE="http://host.docker.internal:11434" beeai_chat_agent
```
