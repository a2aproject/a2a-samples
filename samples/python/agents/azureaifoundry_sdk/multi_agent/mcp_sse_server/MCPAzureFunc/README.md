# MCP Azure Function Server

A serverless Model Context Protocol (MCP) implementation using Azure Functions that provides development tools including git repository operations and IDE integration. This server enables remote agents to access development tools through a standardized MCP interface deployed in Azure's serverless environment.

## 🚀 Overview

The MCP Azure Function Server is a serverless implementation that provides:
- **Git Repository Management**: Clone repositories with progress tracking and error handling
- **IDE Integration**: Open projects in Visual Studio Code and VS Code Insiders
- **Cross-Platform Support**: Works on Windows, macOS, and Linux environments
- **MCP Protocol Compliance**: Standard Model Context Protocol tool implementation
- **Azure Functions Runtime**: Scalable, serverless execution environment

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Tool Agent    │───▶│ MCP Azure Func  │───▶│ Development     │
│                 │    │     Server      │    │     Tools       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ • HTTP Triggers │    │ • Git Clone     │
                       │ • MCP Tools     │    │ • VSCode Open   │
                       │ • Azure Runtime │    │ • File Ops      │
                       │ • Progress Track│    │ • Config Mgmt   │
                       └─────────────────┘    └─────────────────┘
```

## 📂 File Structure

```
MCPAzureFunc/
├── function_app.py          # Main Azure Function application with MCP tools
├── host.json               # Azure Functions host configuration
├── local.settings.json     # Local development settings
├── requirements.txt        # Python dependencies
├── .vscode/               # VS Code configuration for development
├── .gitignore            # Git ignore patterns
└── README.md             # This documentation
```

## 🔧 Components

### 1. Main Application (`function_app.py`)

**Core Function App** - Azure Functions application that:
- Implements MCP tool protocol using custom generic triggers
- Provides git repository cloning with progress tracking
- Enables IDE integration for project management
- Manages repository configuration and state persistence

**Key Features:**
- **Repository Configuration Management**: Persistent storage of cloned repository paths
- **Progress Tracking**: Real-time progress updates for long-running operations
- **Cross-Platform Compatibility**: Supports Windows, macOS, and Linux
- **Error Handling**: Comprehensive error detection and user-friendly messages

### 2. Configuration Files

**`host.json`** - Azure Functions runtime configuration:
- Version 2.0 Azure Functions runtime
- Application Insights integration with sampling
- Experimental extension bundle for custom triggers

**`local.settings.json`** - Local development environment:
- Python runtime configuration
- Local storage emulator settings
- Development-specific environment variables

**`requirements.txt`** - Python dependencies:
- Azure Functions runtime integration
- GitPython for repository operations

## 🎯 Available MCP Tools

### 1. Hello MCP (`hello_mcp`)
**Purpose**: Simple health check and connectivity test
**Parameters**: None
**Returns**: Greeting message confirming MCP server functionality

```json
{
  "status": "success",
  "message": "Hello MCP!"
}
```

### 2. Open VS Code (`open_vscode_mcp`)
**Purpose**: Open files or folders in Visual Studio Code
**Parameters**:
- `path` (string): File or folder path to open in VS Code

**Features**:
- Cross-platform VS Code detection and launching
- Support for both installed and portable VS Code versions
- Path validation and normalization
- Automatic fallback to default VS Code installation paths

**Example Usage**:
```json
{
  "tool_name": "open_vscode_mcp",
  "arguments": {
    "path": "/Users/developer/projects/my-app"
  }
}
```

### 3. Clone GitHub Repository (`clone_github_repo_mcp`)
**Purpose**: Clone GitHub repositories with advanced options
**Parameters**:
- `repo_url` (string): GitHub repository URL to clone
- `branch` (string, optional): Specific branch to clone (defaults to main)
- `depth` (number, optional): Shallow clone depth (defaults to full clone)
- `include_submodules` (boolean, optional): Clone submodules (defaults to false)
