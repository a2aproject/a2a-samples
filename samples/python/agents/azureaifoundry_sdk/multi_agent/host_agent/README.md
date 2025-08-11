# Azure AI Routing Agent

A multi-agent system that uses Azure AI Agents for intelligent task routing and delegation to specialized remote agents.

## 🚀 Features

- **Azure AI Agents Integration**: Core routing logic powered by Azure AI
- **Multi-Agent Coordination**: Intelligent delegation to weather and accommodation specialists
- **Web Interface**: Modern Gradio-based chat interface
- **Real-time Processing**: Streaming responses with status updates
- **Resource Management**: Automatic cleanup and error handling

## 🏗️ Architecture

```
User Request → Azure AI Routing Agent → Remote Specialist Agents
                      ↓
              Weather Agent / Accommodation Agent
```

## 📋 Prerequisites

1. **Azure AI Foundry Project** with model deployment
2. **Azure Authentication** configured (Azure CLI, Service Principal, or Managed Identity)
3. **Remote Agents** running on configured ports
4. **Python 3.13+** with required dependencies

## ⚙️ Configuration

### Environment Variables

Create a `.env` file by copying from the example template:

```bash
cp .env.example .env
```