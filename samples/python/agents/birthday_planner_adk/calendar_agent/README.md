# ADK Agent with Authenticated Tools

This example shows how to create an A2A Server that uses an ADK-based Agent that uses Google-authenticated tools.

This agent also provides an example of how to use server authentication. If an incoming request contains a JWT, the agent will associate the Calendar API authorization with the `sub` of the token and use it for future requests. This way, if the same user interacts with the agent across multiple sessions, authorization can be resued.

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/)
- A Gemini API Key
- A [Google OAuth Client](https://developers.google.com/identity/openid-connect/openid-connect#getcredentials)
  - Configure your OAuth client to handle redirect URLs at `localhost:10007/authenticate`

## Running the example

1. Create the .env file with your API Key and OAuth2.0 Client details

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   echo "GOOGLE_CLIENT_ID=your_client_id_here" >> .env
   echo "GOOGLE_CLIENT_SECRET=your_client_secret_here" >> .env
   ```

2. Run the example

   ```bash
   uv run .
   ```

## Testing the agent

Try running the CLI host at samples/python/hosts/cli to interact with the agent.

```bash
uv run . --agent="http://localhost:10007"
```

To test out providing authentication to the agent, you can use `gcloud` to provide an ID token to the agent.

```bash
uv run . --agent="http://localhost:10007" --header="Authorization=Bearer $(gcloud auth print-identity-token)"
```