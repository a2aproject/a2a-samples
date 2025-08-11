# BeeAI Framework chat Client

This sample uses the [BeeAI Framework](https://docs.beeai.dev/introduction/welcome) to create a simple chat client which communicates using A2A.

## Prerequisites

- Python 3.10 or higher
- [BeeAI Chat agent](../../agents/beeai-chat/README.md) running

## Running the Sample

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
