# Playwright Agent

A specialized remote agent that provides web automation capabilities through Playwright integration using the Model Context Protocol (MCP) and Semantic Kernel. This agent enables browser automation, web scraping, and UI testing functionality within the multi-agent system.

## 🚀 Overview

The Playwright Agent is a remote agent that leverages:
- **Playwright MCP Plugin**: Browser automation through Model Context Protocol
- **Azure AI Agents**: Core intelligence and decision-making
- **Semantic Kernel**: Advanced semantic understanding and plugin management
- **A2A Protocol**: Agent-to-Agent communication for task delegation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Host Agent    │───▶│ Playwright Agent│───▶│  Browser Tasks  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ • Azure AI      │    │ • Navigation    │
                       │ • Semantic      │    │ • Screenshots   │
                       │   Kernel        │    │ • Form Filling  │
                       │ • MCP Plugin    │    │ • Data Extract  │
                       └─────────────────┘    └─────────────────┘
```

## 📂 File Structure

```
playwright_agent/
├── __main__.py              # Main entry point and server startup
├── agent.py                 # Core agent implementation with MCP integration
├── agent_executor.py        # A2A protocol execution handler
├── pyproject.toml          # Project dependencies and configuration
├── uv.lock                 # Dependency lock file
└── README.md               # This documentation
```

## 🔧 Components

### 1. Core Agent (`agent.py`)

**`SemanticKernelMCPAgent`** - Main agent class that:
- Initializes Azure AI Agent with credentials
- Configures Playwright MCP STDIO plugin
- Manages browser automation tasks
- Provides streaming response capabilities

**Key Methods:**
- `initialize_playwright()`: Sets up Playwright MCP plugin with npx command
- `initialize_with_stdio()`: Generic MCP STDIO plugin initialization
- `stream()`: Processes tasks with streaming responses
- `cleanup()`: Proper resource cleanup

### 2. Agent Executor (`agent_executor.py`)

**`SemanticKernelMCPAgentExecutor`** - A2A protocol handler that:
- Implements `AgentExecutor` interface for A2A communication
- Manages task lifecycle and status updates
- Handles event queuing and notifications
- Provides streaming execution with proper error handling

### 3. Server Application (`__main__.py`)

**Main Server** - HTTP server that:
- Exposes agent capabilities via A2A Starlette application
- Defines agent card with Playwright tools skill
- Configures streaming capabilities
- Runs on configurable host and port (default: localhost:10001)

## 🎯 Capabilities

### Browser Automation
- **Navigation**: Visit URLs, handle redirects, manage browser state
- **Element Interaction**: Click, type, scroll, hover actions
- **Form Handling**: Fill forms, submit data, handle file uploads
- **Screenshot Capture**: Full page or element-specific screenshots
- **Content Extraction**: Text content, HTML structure, data scraping

### Advanced Features
- **Multi-tab Management**: Handle multiple browser tabs and windows
- **Wait Conditions**: Wait for elements, network requests, page loads
- **Mobile Emulation**: Test responsive designs and mobile interfaces
- **Performance Monitoring**: Capture network requests and performance metrics

## 📋 Prerequisites

### System Requirements
- **Python 3.13+**
- **Node.js** (for Playwright MCP server)
- **Azure AI Foundry** project with model deployment

### Dependencies
Core dependencies managed via `pyproject.toml`:
```toml
dependencies = [
    "a2a-sdk>=0.2.7",
    "mcp>=1.9.4", 
    "azure-ai-agents>=1.1.0b1",
    "semantic-kernel>=1.33.0",
]
```

## ⚙️ Installation & Setup


### 1. Install Playwright MCP Server

```bash
# Install Playwright MCP package globally
npm install -g @playwright/mcp
```

### 2. Configure Environment
Create a `.env` file by copying from the example template:

```bash
cp .env.example .env
```

