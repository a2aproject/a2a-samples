# BeeAI Framework chat Agent

This sample uses the [BeeAI Framework](https://docs.beeai.dev/introduction/welcome) to create a simple chat agent which communicates using A2A.

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/) installed and running or access to an LLM and API Key

## Running the Sample

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
