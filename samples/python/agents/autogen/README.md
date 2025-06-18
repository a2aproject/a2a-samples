# AutoGen Currency Agent

A specialized agent for currency conversion built with AutoGen framework, integrated with the Agent-to-Agent (A2A) protocol. This agent provides real-time currency exchange rates and supports both synchronous and streaming responses.

## Features

- **Currency Conversion**: Get real-time exchange rates between different currencies
- **Multi-turn Conversations**: Supports context-aware follow-up questions about exchange rates
- **Streaming Responses**: Real-time streaming responses for immediate feedback
- **Session Management**: Maintains conversation context across multiple requests
- **Push Notifications**: Support for webhook-based notifications of task status changes
- **API Integration**: Uses the Frankfurter API to fetch real-time currency exchange data
- **Error Handling**: Robust error handling and validation for all requests
- **JSON-RPC 2.0**: Full compliance with JSON-RPC 2.0 protocol

## Prerequisites

- Python 3.10 or higher
- An OpenAI API key for the language model
- Internet connection for currency exchange rate API calls

## Environment Setup

1. **Clone or download the project files**

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   ```bash
   # Create a .env file with your OpenAI API key
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   ```

   Or create a `.env` file manually with:

   ```
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ```

## Running the Agent

### Basic Usage

Start the agent server with default settings:

```bash
python -m agents.autogen
```

### Custom Configuration

To specify a custom host and port:

```bash
python -m agents.autogen --host 0.0.0.0 --port 8000
```

### Server Information

Once started, the server will:

- Listen on the specified host and port (default: localhost:10000)
- Provide a JSON-RPC 2.0 API endpoint
- Serve JWKS endpoint at `/.well-known/jwks.json` for push notifications
- Log all activities to the console

## API Usage

The agent accepts JSON-RPC 2.0 requests and supports two main methods:

### 1. Synchronous Request (`sendTask`)

For immediate, single-response queries:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "sendTask",
  "params": {
    "id": "task-001",
    "sessionId": "session-001",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "What is the exchange rate from USD to EUR?"
        }
      ]
    },
    "acceptedOutputModes": ["text/plain"],
    "historyLength": 5
  }
}
```

### 2. Streaming Request (`sendTaskSubscribe`)

For real-time streaming responses:

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "sendTaskSubscribe",
  "params": {
    "id": "task-002",
    "sessionId": "session-001",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "What's the exchange rate for JPY to GBP today?"
        }
      ]
    },
    "acceptedOutputModes": ["text/plain"],
    "historyLength": 5
  }
}
```

### 3. Push Notifications (Optional)

Enable webhook notifications for task updates:

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "sendTask",
  "params": {
    "id": "task-003",
    "sessionId": "session-001",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Convert 100 USD to CAD"
        }
      ]
    },
    "acceptedOutputModes": ["text/plain"],
    "pushNotification": {
      "url": "https://your-webhook-endpoint.com/notifications"
    }
  }
}
```

## Example Queries

The agent can handle various currency-related queries:

- **Basic conversion**: "What is the exchange rate from USD to EUR?"
- **Multiple currencies**: "What's the rate for JPY to GBP and USD to CAD?"
- **Historical rates**: "What was the USD to EUR rate on 2024-01-15?"
- **Specific amounts**: "How much is 100 USD in EUR?"
- **Follow-up questions**: After getting a rate, ask "What about GBP?"

## Response Format

### Successful Response

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-001",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "parts": [
          {
            "type": "text",
            "text": "The current exchange rate from USD to EUR is 0.85. This means 1 USD equals 0.85 EUR."
          }
        ],
        "index": 0
      }
    ]
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "OPENAI_API_KEY environment variable not set."
  }
}
```

## Architecture

The agent uses AutoGen to orchestrate interactions between:

- **Assistant Agent**: Interprets user queries and determines appropriate responses
- **User Proxy Agent**: Executes the exchange rate tool function
- **Currency Tool**: Fetches real-time data from the Frankfurter API
- **Task Manager**: Manages request lifecycle, streaming, and notifications
- **A2A Server**: Provides JSON-RPC 2.0 API interface

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required - Your OpenAI API key
- `HOST`: Optional - Server host (default: localhost)
- `PORT`: Optional - Server port (default: 10000)

### Supported Features

- **Content Types**: `text`, `text/plain`
- **Streaming**: Yes
- **Push Notifications**: Yes
- **Session Management**: Yes
- **Multi-currency**: Yes
- **Historical Data**: Yes (via date parameter)

## Development

### Project Structure

```
agents/autogen/
├── __init__.py          # Package initialization
├── __main__.py          # Server entry point
├── agent.py             # Core AutoGen agent implementation
├── task_manager.py      # Task lifecycle management
└── requirements.txt     # Python dependencies
```

### Testing

You can test the agent using curl or any HTTP client:

```bash
curl -X POST http://localhost:10000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "sendTask",
    "params": {
      "id": "test-task",
      "sessionId": "test-session",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "USD to EUR rate?"}]
      },
      "acceptedOutputModes": ["text/plain"]
    }
  }'
```

### Extending the Agent

To add new functionality:

1. **Add new tools** to the `CurrencyAgent` class
2. **Update the system instruction** to include new capabilities
3. **Modify the task manager** if new response types are needed
4. **Update the agent card** to reflect new skills

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY environment variable not set"**

   - Ensure your `.env` file contains a valid OpenAI API key
   - Check that the `.env` file is in the correct directory

2. **"API request failed"**

   - Check your internet connection
   - Verify the Frankfurter API is accessible
   - Ensure currency codes are valid (3-letter ISO codes)

3. **"Port already in use"**

   - Use a different port: `python -m agents.autogen --port 8001`
   - Check for other running processes on the port

4. **JSON parsing errors**
   - Ensure requests follow JSON-RPC 2.0 format exactly
   - Check for proper JSON syntax and required fields

### Logging

The agent logs important events to the console. For debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is part of the AutoGen agent samples and follows the same licensing terms.
