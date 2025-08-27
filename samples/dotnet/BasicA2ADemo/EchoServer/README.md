# Echo Server

A simple A2A agent that echoes back any message you send to it. This is the perfect starting point for understanding how A2A agents work.

## What This Agent Does

The Echo Agent is the simplest possible A2A agent. It:
- Receives any text message
- Responds with the same message prefixed with "Echo: "
- Demonstrates the basic A2A agent structure

## Key Files

- **`EchoAgent.cs`** - The main agent implementation
- **`Program.cs`** - ASP.NET Core server setup
- **`EchoServer.csproj`** - Project configuration

## Running the Echo Server

```bash
cd EchoServer
dotnet run
```

The server will start on `http://localhost:5001`

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Welcome message and server info |
| `/` | POST | A2A JSON-RPC communication endpoint |
| `/.well-known/agent.json` | GET | Agent discovery (agent card) |
| `/health` | GET | Health check |

## Testing the Agent

### 1. Check if it's running
```bash
curl http://localhost:5001/health
```

### 2. Get the agent card
```bash
curl http://localhost:5001/.well-known/agent.json
```

### 3. Send a message via A2A protocol
Use the SimpleClient project or any A2A-compatible client to send messages.

## Learning Points

### Agent Implementation (`EchoAgent.cs`)

```csharp
public class EchoAgent : IAgent
{
    // Agent metadata
    public string Name => "Simple Echo Agent";
    public string Description => "...";
    public Version Version => new(1, 0, 0);

    // Handle incoming messages
    public Task<AgentResponse> OnMessageAsync(Message message, CancellationToken cancellationToken)
    {
        // Extract text from message
        var userText = GetTextFromMessage(message);
        
        // Create response
        var responseText = $"Echo: {userText}";
        var responseMessage = new Message { /* ... */ };
        
        return Task.FromResult(new AgentResponse { Message = responseMessage });
    }

    // Provide agent capabilities
    public Task<AgentCard> OnAgentCardQuery(string agentUrl, CancellationToken cancellationToken)
    {
        // Return agent metadata and capabilities
    }
}
```

### Server Setup (`Program.cs`)

```csharp
// Create task manager
var taskManager = new TaskManager();

// Create and attach agent
var echoAgent = new EchoAgent();
echoAgent.Attach(taskManager);

// Map A2A endpoints
app.MapA2A(taskManager, "/");                    // JSON-RPC
app.MapWellKnownAgentCard(taskManager, "/");     // Agent discovery
```

## Key Concepts Demonstrated

1. **IAgent Interface** - Every A2A agent implements this interface
2. **Message Handling** - How to process incoming messages
3. **Agent Cards** - How agents advertise their capabilities
4. **Task Manager** - The A2A protocol handler
5. **Endpoint Mapping** - Setting up A2A communication endpoints

## Next Steps

After understanding the Echo Agent:
1. Look at the **CalculatorServer** for more complex business logic
2. Examine the **SimpleClient** to see how clients communicate with agents
3. Try modifying the echo response format
4. Add logging or additional functionality

## Common Patterns

This agent demonstrates these A2A patterns:
- ✅ Simple message processing
- ✅ Text extraction from messages
- ✅ Response message creation
- ✅ Agent capability advertisement
- ✅ Basic error handling
