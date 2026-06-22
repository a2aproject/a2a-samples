# Signing and Verifying Example

Signed agent used as an example for AgentCard signing and verifying.

Read more about signing and verifying AgentCards here: [Agent Card Signing](https://a2a-protocol.org/latest/specification/#84-agent-card-signing).

## Getting started

1. Setup the virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the server:

   ```bash
   python3 __main__.py
   ```

3. Run the test client:

   ```bash
   python3 test_client.py
   ```

## Build Container Image

Agent can also be built using a container file.

1. Navigate to the directory `samples/python/agents/signing_and_verifying` directory:

  ```bash
  cd samples/python/agents/signing_and_verifying
  ```

2. Build the container file

    ```bash
    podman build . -t signing_and_verifying-a2a-server
    ```

> [!Tip]  
> Podman is a drop-in replacement for `docker` which can also be used in these commands.

3. Run your container

    ```bash
    podman run -p 9999:9999 signing_and_verifying-a2a-server
    ```

## Validate

To validate in a separate terminal, run the A2A CLI host:

```bash
cd ../../hosts/cli
# Setup the CLI host's environment if you haven't already:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Run the CLI host pointing to our agent:
python3 __main__.py --agent http://localhost:9999
```


## Disclaimer
Important: The sample code provided is for demonstration purposes
and illustrates the mechanics of the Agent-to-Agent (A2A) protocol.
When building production applications, it is critical to treat any agent
operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard,
messages, artifacts, and task statuses—should be handled as untrusted input.
For example, a malicious agent could provide an AgentCard containing crafted data
in its fields (e.g., description, name, skills.description). If this data is used
without sanitization to construct prompts for a Large Language Model (LLM),
it could expose your application to prompt injection attacks. Failure to properly
validate and sanitize this data before use can introduce security vulnerabilities
into your application.

Developers are responsible for implementing appropriate security measures,
such as input validation and secure handling of credentials to protect their systems and users.
