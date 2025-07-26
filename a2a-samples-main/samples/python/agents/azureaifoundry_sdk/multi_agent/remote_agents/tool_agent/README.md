# Tool Agent

A specialized remote agent that provides comprehensive development and task assistance through Model Context Protocol (MCP) tools. This agent enables git operations, IDE integration, and various development utilities within the multi-agent system.

## 🚀 Overview

The Tool Agent is a versatile remote agent that leverages:
- **MCP SSE Plugin**: Development tools through Model Context Protocol Server-Sent Events
- **Azure AI Agents**: Core intelligence and decision-making capabilities
- **Semantic Kernel**: Advanced semantic understanding and plugin management
- **A2A Protocol**: Agent-to-Agent communication for seamless task delegation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Host Agent    │───▶│   Tool Agent    │───▶│  Dev Tools MCP  │
│                 │    │                 │    │     Server      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ • Azure AI      │    │ • Git Clone     │
                       │ • Semantic      │    │ • VSCode Open   │
                       │   Kernel        │    │ • File Ops      │
                       │ • MCP SSE       │    │ • Development   │
                       └─────────────────┘    └─────────────────┘
```

## 📂 File Structure

```
tool_agent/
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
- Initializes Azure AI Agent with Azure credentials
- Configures MCP SSE plugin for development tools
- Manages development task execution and tool coordination
- Provides both streaming and synchronous response capabilities

**Key Methods:**
- `initialize(mcp_url)`: Sets up MCP SSE plugin with configurable server URL
- `invoke(user_input, session_id)`: Synchronous task processing with complete responses
- `stream(user_input, session_id)`: Asynchronous streaming task execution
- `cleanup()`: Proper resource cleanup and connection management

### 2. Agent Executor (`agent_executor.py`)

**`SemanticKernelMCPAgentExecutor`** - A2A protocol handler that:
- Implements `AgentExecutor` interface for standardized agent communication
- Manages task lifecycle with comprehensive status tracking
- Handles event queuing and real-time notifications
- Provides streaming execution with robust error handling and recovery

### 3. Server Application (`__main__.py`)

**Main Server** - HTTP server that:
- Exposes agent capabilities via A2A Starlette application
- Defines comprehensive agent card with development tools skills
- Configures streaming capabilities for real-time responses
- Runs on configurable host and port (default: localhost:10002)

## 🎯 Capabilities

### Development Tools
- **Git Operations**: Repository cloning, branch management, commit operations
- **IDE Integration**: VSCode and VSCode Insiders project opening
- **File Management**: File system operations, directory navigation
- **Project Setup**: Development environment initialization

### Advanced Features
- **Repository Management**: Clone repositories and open in preferred IDE
- **Development Workflow**: Streamlined development task automation
- **Tool Chain Integration**: Seamless integration with development tools
- **Cross-Platform Support**: Works across different operating systems

## 📋 Prerequisites

### System Requirements
- **Python 3.13+**
- **MCP Server**: Running development tools MCP server
- **Azure AI Foundry** project with model deployment
- **Git**: For repository operations (optional)
- **VSCode/VSCode Insiders**: For IDE integration (optional)

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

### 1. Install Dependencies
```bash
cd remote_agents/tool_agent

# Using uv (recommended)
uv sync
```


### 3. Configure Environment
Create a `.env` file by copying from the example template:

```bash
cp .env.example .env
```


### Example Tasks

The agent can handle various development and tool-related tasks:

**Git Operations:**
```
"Clone https://github.com/kinfey/mcpdemo1"
"Clone the repository and open it in VSCode"
"Clone https://github.com/user/repo and open with VSCode Insiders"
```

