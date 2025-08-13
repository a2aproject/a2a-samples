# Hello World Azure AI Foundry Agent

A simple example demonstrating how to create and interact with an Azure AI Foundry agent through a modern web interface.

## Overview

This is a "Hello World" example that shows the basic structure and usage of an Azure AI Foundry agent with a Starlette web application. The application provides:

- **Modern Web Interface**: Real-time chat interface with WebSocket support
- **RESTful API**: Standard HTTP endpoints for integration
- **Real-time Communication**: WebSocket-based messaging for instant responses
- **Session Management**: Automatic session creation and cleanup
- **Error Handling**: Comprehensive error handling and user feedback

## Features

- 🌐 **Modern Web UI**: Clean, responsive chat interface
- ⚡ **Real-time Chat**: WebSocket-based communication
- 📱 **Mobile Friendly**: Responsive design that works on all devices
- 🔄 **Auto-reconnect**: Automatic reconnection on connection loss
- 💬 **Typing Indicators**: Visual feedback during agent processing
- 🎨 **Beautiful Design**: Modern gradient design with smooth animations
- 🌙 **Dark Mode**: Automatic dark mode support based on system preferences

## Prerequisites

1. **Azure AI Foundry Project** with a deployed language model
2. **Azure Authentication** configured (Azure CLI, Service Principal, or Managed Identity)
3. **Python 3.11+**

## Setup

### 1. Environment Configuration

Create a `.env` file from the template:

```bash
cp .env.template .env
```

Edit the `.env` file and set your Azure AI Foundry credentials:

```env
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=your-model-deployment-name
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 3. Run the Application

```bash
# Web interface (default)
uv run python -m hello_world_agent

# Or using the CLI
python cli.py web

# Console demo
python cli.py console
```

## Project Structure

```
hello_world_agent/
├── README.md              # This file
├── pyproject.toml         # Project configuration and dependencies
├── .env.template          # Environment variables template
├── __main__.py           # Entry point for the web application
├── web_app.py            # Starlette web application
├── hello_agent.py        # Core agent implementation
├── cli.py                # Command-line interface
├── utils.py              # Utility functions
├── client.py             # Example client for testing
├── templates/            # HTML templates
│   └── index.html        # Main chat interface
├── static/               # Static files (CSS, JS)
│   └── style.css         # Additional styles
├── examples/             # Usage examples
│   ├── simple_chat.py    # Basic interaction example
│   ├── multi_turn.py     # Multi-turn conversation
│   └── error_handling.py # Error handling demo
└── tests/                # Test files
    └── test_hello_agent.py
```

## 🚀 Usage

### Web Interface (Default)

The easiest way to use the agent is through the web interface:

```bash
# Using uv (recommended)
uv run python -m hello_world_agent

# Or using pip
python -m hello_world_agent

# Or using the CLI
python cli.py web
```

Then open your browser to `http://localhost:8000`

### Command Line Interface

For more control, use the CLI:

```bash
# Web server with custom port
python cli.py web --port 3000

# Console demo (original command-line interface)
python cli.py console

# Check environment configuration
python cli.py check --verbose

# Show help and information
python cli.py info
```

### API Endpoints

The web application also provides REST API endpoints:

- `GET /` - Web interface
- `GET /health` - Health check and environment validation  
- `POST /api/session` - Create a new chat session
- `POST /api/message` - Send a message to the agent
- `POST /api/session/delete` - Delete a session
- `WebSocket /ws` - Real-time WebSocket communication

## Usage Examples

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Wait for the "Connected!" status message
3. Start chatting with the agent
4. The interface supports:
   - Real-time messaging via WebSocket
   - Typing indicators
   - Mobile-responsive design
   - Dark mode (automatic based on system preference)

### Programmatic Usage

```python
import asyncio
from hello_world_agent.hello_agent import HelloWorldAgent

async def main():
    agent = HelloWorldAgent()
    await agent.create_agent()
    
    # Create a conversation thread
    thread = await agent.create_thread()
    
    # Send a message and get response
    response = await agent.run_conversation(
        thread.id, 
        "Hello! What can you do?"
    )
    print(f"Agent: {response[0]}")
    
    await agent.cleanup_agent()

if __name__ == "__main__":
    asyncio.run(main())
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT` | Your Azure AI Foundry project endpoint | `https://your-project.cognitiveservices.azure.com/` |
| `AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME` | The name of your deployed model | `gpt-4` |

## Features Demonstrated

- **Agent Creation**: How to create an Azure AI Foundry agent
- **Thread Management**: Creating and managing conversation threads
- **Message Handling**: Sending messages and receiving responses
- **Error Handling**: Basic error handling and cleanup
- **Environment Configuration**: Using environment variables for configuration

## Next Steps

This hello world example can be extended to:

1. **Add Tools/Functions**: Implement custom functions the agent can call
2. **Add Memory**: Implement conversation memory and context
3. **Add UI**: Create a web interface using Gradio or Streamlit
4. **Add Logging**: Implement comprehensive logging
5. **Add Testing**: Write comprehensive tests for your agent

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure you're authenticated with Azure CLI or have proper credentials configured
2. **Model Not Found**: Verify your model deployment name is correct
3. **Endpoint Issues**: Check that your Azure AI Foundry project endpoint is correct

### Debug Mode

Set the environment variable for verbose logging:

```bash
export PYTHONPATH=.
export AZURE_LOG_LEVEL=DEBUG
python -m hello_world_agent
```
