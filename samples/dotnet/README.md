# .NET A2A Samples

This folder contains .NET demonstrations of the A2A (Agent-to-Agent) SDK, showcasing different patterns and use cases for building intelligent agents.

## Available Demos

### 🏗️ BasicA2ADemo
A foundational example demonstrating core A2A concepts with simple agents.

**What's included:**
- **EchoServer**: Basic message echoing agent
- **CalculatorServer**: Simple math operations agent  
- **SimpleClient**: Interactive client for both agents

**Key concepts:** Agent discovery, message-based communication, task handling

[→ View BasicA2ADemo](./BasicA2ADemo/)

### 🖥️ CLIAgent (A2ACliDemo)
Shows how to build agents that can execute system commands safely.

**What's included:**
- **CLIServer**: Agent that executes whitelisted CLI commands
- **CLIClient**: Interactive command-line interface

**Key concepts:** System integration, security constraints, cross-platform execution

[→ View CLIAgent](./CLIAgent/)

## Getting Started

Each demo includes:
- 📖 Detailed README with setup instructions
- 🚀 Quick-start batch scripts for Windows
- 💡 Example commands and use cases
- 🔧 Complete source code with comments

## Requirements

- .NET 9.0 SDK
- Windows, Linux, or macOS
- A2A SDK (included via NuGet)

## Quick Start

1. **Choose a demo** from the list above
2. **Follow the README** in that demo's folder
3. **Run the batch script** for instant setup, or
4. **Manual setup** with `dotnet run` commands

## Learning Path

1. **Start with BasicA2ADemo** - Learn fundamental A2A patterns
2. **Explore CLIAgent** - See system integration in action
3. **Build your own** - Use these as templates for custom agents

Each demo builds upon concepts from the previous ones, providing a clear progression from basic agent communication to advanced system integration.
