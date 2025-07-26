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


## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.