# .NET GitHub Agent with Semantic Kernel, MCP, and A2A

This .NET 8 project demonstrates how to build an intelligent GitHub agent that combines three powerful AI technologies:

1. **[Microsoft Semantic Kernel](https://github.com/microsoft/semantic-kernel)** - AI orchestration framework for LLM integration
2. **[Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/servers)** - Standardized protocol for AI tool integration  
3. **[Google Agent-to-Agent (A2A)](https://github.com/google/A2A)** - Protocol for agent communication and task management

## What This Project Does

This sample creates a GitHub agent server that can:
- Answer questions about GitHub repositories using natural language
- Analyze code, issues, pull requests, and repository statistics
- Communicate with other agents via the A2A protocol
- Expose both REST API and A2A endpoints for different integration needs

## Architecture Overview

The solution consists of three main projects:

### 🏗️ **Server** (`src/Server/`)
ASP.NET Core web API server that hosts the GitHub agent:
- **`GitHubAgentController`** - REST API endpoints for testing and direct queries
- **`HealthController`** - Health checks and system status
- **`GitHubA2AAgent`** - Main service that implements A2A protocol integration
- **A2A Endpoint** - `/github-agent` for standard agent-to-agent communication

### 🤖 **GitHub Agent** (`src/Agents/Github/`)
Core agent implementation using Semantic Kernel:
- **`KernelBuilder`** - Configures Semantic Kernel with OpenAI and MCP tools
- **`AgentFactory`** - Creates ChatCompletionAgent instances
- **`AgentService`** - Processes queries through the agent
- **`McpClientFactory`** - Connects to GitHub MCP server via stdio transport
- **`ToolService`** - Retrieves GitHub tools from MCP server

### 🖥️ **CLI Client** (`src/Client.Cli/`)
Command-line interface for interacting with the agent:
- **A2A Mode** - Full agent-to-agent communication with file attachments
- **API Mode** - Direct REST API calls for testing
- **Interactive Mode** - Real-time session with command switching
- **Status & Tools** - Inspect agent health and available capabilities

## How It Works

### 🔄 **Integration Flow**
1. **MCP Server Connection** - Connects to `@modelcontextprotocol/server-github` via stdio transport
2. **Tool Discovery** - Retrieves GitHub-specific tools (repository search, file reading, issue tracking, etc.)
3. **Kernel Setup** - Builds Semantic Kernel with OpenAI LLM and GitHub tools as plugins
4. **Agent Creation** - Creates ChatCompletionAgent with GitHub-focused instructions
5. **A2A Registration** - Exposes agent via A2A protocol for inter-agent communication

### 🛠️ **Key Technologies**

**Semantic Kernel Integration:**
```csharp
// Builds kernel with OpenAI and MCP tools
Kernel kernel = builder.Build();
kernel.Plugins.AddFromFunctions("GitHub", tools.Select(t => t.AsKernelFunction()));
```

**MCP GitHub Server Connection:**
```csharp
// Connects to GitHub MCP server
new StdioClientTransport(new StdioClientTransportOptions
{
    Name = "MCPServer", 
    Command = "npx",
    Arguments = ["-y", "@modelcontextprotocol/server-github"]
});
```

**A2A Agent Registration:**
```csharp
// Exposes agent via A2A protocol
app.MapA2A(taskManager, "/github-agent");
taskManager.OnMessageReceived = ProcessMessageAsync;
```

## Getting Started

### Prerequisites

- **.NET 8 SDK** - For building and running the application
- **Node.js** - Required for MCP GitHub server (`@modelcontextprotocol/server-github`)
- **OpenAI API Key** - For LLM integration

### Setup & Configuration

1. **Environment Variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export OPENAI_MODEL_NAME="gpt-4o-mini"  # Optional, defaults to gpt-4o-mini
   ```

2. **Build the Solution:**
   ```bash
   dotnet build
   ```

### Running the Application

#### 🏃 **Start the Server:**
```bash
cd src/Server
dotnet run
```
The server will start on:
- HTTP: `http://localhost:5000`
- HTTPS: `https://localhost:5001`
- Swagger UI: `https://localhost:5001/swagger`

#### 🖥️ **Use the CLI Client:**
```bash
cd src/Client.Cli

# Interactive mode with both A2A and API support
dotnet run -- interactive --agent-url https://localhost:5001

# Direct A2A communication
dotnet run -- a2a --agent-url https://localhost:5001

# Direct API calls (for testing)
dotnet run -- api --agent-url https://localhost:5001 --query "What repositories does microsoft have?"

# Check agent status
dotnet run -- status --agent-url https://localhost:5001
```

## Example Queries

Once running, you can ask the GitHub agent questions like:

```
🤖 github-agent> What repositories does microsoft have?
🤖 github-agent> Show me the latest commits in microsoft/semantic-kernel
🤖 github-agent> What are the open issues in facebook/react?
🤖 github-agent> Who are the top contributors to rust-lang/rust?
```

## API Endpoints

### REST API (for testing)
- `GET /api/githubagent/status` - Agent status and capabilities
- `POST /api/githubagent/query` - Direct query processing  
- `GET /api/githubagent/tools` - Available GitHub tools
- `POST /api/githubagent/reinitialize` - Reinitialize agent
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies

### A2A Protocol
- `POST /github-agent` - Standard A2A message endpoint
- Supports both text messages and file attachments
- Returns responses in A2A Message format

## Technical Implementation

### MCP Tool Integration
The agent dynamically loads GitHub tools from the MCP server:
```csharp
// Tools are automatically converted to Semantic Kernel functions
kernel.Plugins.AddFromFunctions("GitHub", 
    tools.Select(tool => tool.AsKernelFunction()));
```

### A2A Message Processing
Messages are processed through the Semantic Kernel agent:
```csharp
ChatMessageContent response = await agentService.ProcessQuery(query, cancellationToken);
return new Message { 
    Parts = [new TextPart { Text = response.Content }] 
};
```

## Project Structure

```
dotnet.sln                          # Solution file
├── src/
│   ├── Server/                     # ASP.NET Core API server
│   │   ├── Controllers/            # REST API controllers
│   │   ├── Services/              # GitHubA2AAgent service
│   │   ├── Models/                # Request/Response models
│   │   └── Program.cs             # Server entry point
│   │
│   ├── Agents/Github/             # Core agent implementation
│   │   ├── KernelBuilder.cs       # Semantic Kernel configuration
│   │   ├── AgentFactory.cs        # Agent creation
│   │   ├── AgentService.cs        # Query processing
│   │   ├── McpClientFactory.cs    # MCP client setup
│   │   └── ToolService.cs         # GitHub tool management
│   │
│   └── Client.Cli/               # Command-line interface
│       ├── Commands/             # CLI command definitions
│       ├── Services/             # A2A and API services
│       └── Program.cs            # CLI entry point
```

## Dependencies

### NuGet Packages
- **A2A** (0.1.0-preview.2) - Google's Agent-to-Agent protocol
- **Microsoft.SemanticKernel** (1.48.0) - AI orchestration framework
- **ModelContextProtocol** (0.1.0-preview.12) - MCP client library
- **System.CommandLine** (2.0.0-beta4) - CLI framework

### External Services
- **OpenAI API** - LLM provider (GPT-4o-mini by default)
- **MCP GitHub Server** - `@modelcontextprotocol/server-github` via npm

## Resources

- [Semantic Kernel Documentation](https://github.com/microsoft/semantic-kernel)
- [Model Context Protocol](https://github.com/modelcontextprotocol/servers)
- [Google A2A Protocol](https://github.com/google/A2A)
- [MCP GitHub Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
