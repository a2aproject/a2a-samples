# Hello World Example

Hello World example agent that only returns Message events

## Getting started

1. Start the server

   ```bash
   uv run .
   ```

2. Run the test client

   ```bash
   uv run test_client.py
   ```

## Build Container Image

Agent can also be built using a container file.

1. Navigate to the directory `samples/python/agents/helloworld` directory:

  ```bash
  cd samples/python/agents/helloworld
  ```

2. Build the container file

    ```bash
    podman build . -t helloworld-a2a-server
    ```

> [!Tip]  
> Podman is a drop-in replacement for `docker` which can also be used in these commands.

3. Run you container

    ```bash
    podman run -p 9999:9999 helloworld-a2a-server
    ```

## Validate

To validate in a separate terminal, run the A2A client:

```bash
cd samples/python/hosts/cli
uv run . --agent http://localhost:9999
```
