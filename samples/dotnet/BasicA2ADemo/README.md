# Basic A2A .NET Demo

This is a simple demonstration of the A2A (Agent-to-Agent) .NET SDK that shows the basics of agent communication.

## What's Included

- **EchoServer**: A simple agent that echoes back any message you send to it
- **CalculatorServer**: A basic calculator agent that can perform simple math operations
- **SimpleClient**: A console application that demonstrates how to communicate with both agents

## Getting Started

### Option 1: Quick Start (Windows)

Use the provided batch script to run everything automatically:

```bash
run-demo.bat
```

This will start both agent servers and the client in separate windows.

### Option 2: Manual Setup

#### 1. Start the Agent Servers

In separate terminals, start each server:

```bash
# Start the Echo Agent (runs on port 5001)
cd EchoServer
dotnet run

# Start the Calculator Agent (runs on port 5002)
cd CalculatorServer
dotnet run
```

#### 2. Run the Client

In another terminal:

```bash
cd SimpleClient
dotnet run
```

The client will automatically discover and communicate with both agents, demonstrating:
- Agent discovery via agent cards
- Message-based communication
- Task-based communication
- Error handling

## Key Concepts Demonstrated

### Agent Discovery
- How agents advertise their capabilities through agent cards
- How clients discover and connect to agents

### Message-Based Communication
- Simple request-response pattern
- Immediate responses without task tracking

### Task-Based Communication
- Creating persistent tasks
- Tracking task progress and status
- Retrieving task results

### Multiple Agents
- Running multiple agents simultaneously
- Client communicating with different agent types
- Agent-specific functionality

## Project Structure

```text
BasicA2ADemo/
├── README.md                    # This file
├── EchoServer/
│   ├── EchoServer.csproj       # Echo agent project
│   ├── Program.cs              # Echo server startup
│   └── EchoAgent.cs            # Echo agent implementation
├── CalculatorServer/
│   ├── CalculatorServer.csproj # Calculator agent project
│   ├── Program.cs              # Calculator server startup
│   └── CalculatorAgent.cs      # Calculator agent implementation
└── SimpleClient/
    ├── SimpleClient.csproj     # Client project
    └── Program.cs              # Client implementation
```

This demo provides a foundation for understanding how to build agent-to-agent communication systems with the A2A .NET SDK.
