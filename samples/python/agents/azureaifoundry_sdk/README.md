# A2A Samples for Azure AI Foundry Agent SDK

This directory contains two comprehensive examples demonstrating how to integrate **Azure AI Foundry Agent Service** with Google's **Agent-to-Agent (A2A) Protocol**. These samples showcase different approaches to building intelligent agents using Azure's AI services.

## 🔋 Core Technologies

- **Azure AI Foundry Agent Service**: Intelligent agent capabilities with Azure AI
- **Google A2A SDK**: Agent-to-agent communication framework
- **Model Context Protocol (MCP)**: Standardized tool communication
- **Azure Functions**: Serverless hosting for MCP services

## 📁 Examples Overview

### 1. Azure Foundry Agent (`./azurefoundryagent`)

A **calendar management agent** that demonstrates core Azure AI Foundry integration with A2A protocol.

#### Key Features:
- 🤖 **AI Foundry Integration**: Build intelligent agents using Azure AI Foundry
- 📅 **Calendar Management**: Check schedule availability, get upcoming events
- 🔄 **A2A Framework**: Support agent-to-agent communication and collaboration
- 💬 **Conversation Capabilities**: Natural language processing and multi-turn conversations
- 🛠️ **Tool Integration**: Simulated calendar API tool integration

#### Use Cases:
- "Check my calendar for tomorrow"
- "What meetings do I have this week?"
- "Am I available on Friday afternoon?"

#### Technologies:
- Azure AI Foundry Agent Service
- Azure AI Projects SDK
- A2A SDK for Python
- Starlette web framework

### 2. Currency Agent Demo (`./currencyagentdemo`)

A **comprehensive currency exchange system** combining Azure AI Foundry, MCP services, and A2A protocol for real-time currency conversion.

#### Architecture Components:
1. **🔌 MCP Server**: Azure Functions-based service providing currency exchange tools
2. **💱 Currency Agent**: Azure AI Foundry agent integrated with A2A protocol

#### Key Features:
- **🎯 Azure AI Agent Service**: Leverages Azure AI Foundry for intelligent responses
- **🔧 Model Context Protocol (MCP)**: Standardized tool communication protocols
- **🤝 Google A2A SDK**: Agent-to-agent communication framework
- **☁️ Azure Functions**: Serverless MCP service hosting
- **💰 Real-time Exchange Rates**: Uses Frankfurter API for live currency data
- **📡 Streaming Responses**: Real-time response streaming

#### Available Tools:
- `hello_mcp`: Connectivity test tool
- `get_exchange_rate`: Currency conversion with `currency_from` and `currency_to` parameters

#### Use Cases:
- "Convert 100 USD to EUR"
- "What's the current exchange rate from GBP to JPY?"
- "How much is 50 CAD in Australian dollars?"

#### Technologies:
- Azure AI Foundry Agent Service
- Azure Functions (for MCP server)
- Model Context Protocol (MCP)
- A2A SDK for Python
- Frankfurter API for exchange rates

## 🚀 Getting Started

### Prerequisites
- Python 3.12+ (azurefoundryagent) or Python 3.13+ (currencyagentdemo)
- Azure AI Foundry project and deployment
- Azure subscription (for Functions in currency demo)
- UV package manager (recommended)

### Quick Setup
1. Choose an example directory
2. Copy `.env.template` to `.env` and configure Azure settings
3. Install dependencies: `uv sync`
4. Run the agent: `uv run .`

### Required Environment Variables
```env
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=Your Azure AI Foundry Project Endpoint
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=Your Azure AI Foundry Deployment Model Name
```

## 🎯 When to Use Each Example

### Use Azure Foundry Agent when you want to:
- Learn core Azure AI Foundry + A2A integration
- Build simple tool-based agents
- Understand basic calendar/scheduling functionality
- Get started with minimal setup

### Use Currency Agent Demo when you want to:
- Build production-ready agents with external services
- Implement MCP protocol with Azure Functions
- Create agents that interact with real-time APIs
- Understand complex multi-service architecture

Both examples provide complete implementations with detailed documentation and are ready for extension and customization.