# Dice Agent (REST)

A minimal A2A agent that rolls dice and returns the result over the HTTP/JSON transport. Good for testing connectivity and latency without LLM overhead.

## Prerequisites
- Python 3.10+
- `uv` (or `pip`) to install dependencies

## Install
```bash
cd samples/python/agents/dice_agent_rest
uv sync  # or: pip install -r requirements.txt
```

## Run the agent
```bash
uv run .
# Agent listens on http://0.0.0.0:9999 by default
```

## Try it with curl
```bash
curl -X POST http://localhost:9999/message \
  -H 'Content-Type: application/json' \
  -d '{
        "id": "req-1",
        "params": {
          "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "roll a d6"}],
            "messageId": "msg-1"
          }
        }
      }'
```

Example response (simplified):
```json
{
  "result": {
    "parts": [{"kind": "text", "text": "You rolled a 4"}]
  }
}
```

## Agent card
The public agent card is available at:
```
http://localhost:9999/.well-known/agent-card.json
```


