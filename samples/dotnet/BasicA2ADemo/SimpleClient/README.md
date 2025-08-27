# Simple Client

A console application that demonstrates how to discover and communicate with A2A agents. This shows the client-side patterns for agent-to-agent communication.

## What This Client Does

The Simple Client demonstrates:
- **Agent Discovery** - How to find and connect to agents
- **Agent Card Retrieval** - Getting agent capabilities and metadata
- **Message Communication** - Sending messages and receiving responses
- **Multi-Agent Coordination** - Communicating with different types of agents
- **Error Handling** - Graceful handling of communication failures

## Key Files

- **`Program.cs`** - Main client implementation with all demo logic
- **`SimpleClient.csproj`** - Project configuration

## Running the Client

### Prerequisites
Make sure both agent servers are running:
```bash
# Terminal 1 - Echo Agent
cd ../EchoServer
dotnet run

# Terminal 2 - Calculator Agent  
cd ../CalculatorServer
dotnet run
```

### Run the Client
```bash
cd SimpleClient
dotnet run
```

## What the Demo Shows

### 1. Agent Discovery Flow
```
🔍 Discovering Echo Agent...
✅ Found agent: Simple Echo Agent
   📝 Description: A basic agent that echoes back any message...
   🔢 Version: 1.0.0
   🎯 Capabilities: 1
      • Echo Messages: Echoes back any text message sent to it
```

### 2. Agent Communication
```
💬 Communicating with Echo Agent...
   📤 Sending: Hello, Echo Agent!
   📥 Received: Echo: Hello, Echo Agent!
   📤 Sending: Can you repeat this message?
   📥 Received: Echo: Can you repeat this message?
```

### 3. Different Agent Types
The client automatically adapts its communication based on the agent type:
- **Echo Agent**: Sends friendly test messages
- **Calculator Agent**: Sends mathematical expressions

## Learning Points

### Agent Discovery Pattern

```csharp
static async Task<AgentCard> DiscoverAgent(string agentUrl)
{
    // Create a card resolver for the agent
    var cardResolver = new A2ACardResolver(new Uri(agentUrl));
    
    // Fetch the agent card
    var agentCard = await cardResolver.GetAgentCardAsync();
    
    // Display agent information
    Console.WriteLine($"✅ Found agent: {agentCard.Name}");
    Console.WriteLine($"   📝 Description: {agentCard.Description}");
    
    return agentCard;
}
```

### Client Communication Pattern

```csharp
static async Task CommunicateWithAgent(string agentUrl)
{
    // Create an A2A client for this agent
    var client = new A2AClient(new Uri(agentUrl));
    
    // Create a message
    var message = new Message
    {
        Role = MessageRole.User,
        MessageId = Guid.NewGuid().ToString(),
        Parts = [new TextPart { Text = "Hello, agent!" }]
    };
    
    // Send message and get response
    var response = await client.SendMessageAsync(new MessageSendParams { Message = message });
    var responseText = GetTextFromMessage((Message)response);
    
    Console.WriteLine($"Response: {responseText}");
}
```

### Message Creation Helper

```csharp
static Message CreateMessage(string text)
{
    return new Message
    {
        Role = MessageRole.User,           // Identifies this as a user message
        MessageId = Guid.NewGuid().ToString(), // Unique message identifier
        Parts = [new TextPart { Text = text }]  // Message content
    };
}
```

### Response Processing

```csharp
static string GetTextFromMessage(Message message)
{
    var textPart = message.Parts.OfType<TextPart>().FirstOrDefault();
    return textPart?.Text ?? "[No text content]";
}
```

## Key Concepts Demonstrated

### 1. Agent Discovery Workflow
1. **Endpoint Definition** - Know the agent's base URL
2. **Card Resolution** - Fetch `/.well-known/agent.json`
3. **Capability Analysis** - Understand what the agent can do
4. **Connection Setup** - Create A2A client for communication

### 2. Message-Based Communication
1. **Message Construction** - Create properly formatted A2A messages
2. **Request Sending** - Use `SendMessageAsync()` for communication
3. **Response Processing** - Extract and display agent responses
4. **Error Handling** - Handle network and protocol errors

### 3. Multi-Agent Patterns
1. **Agent Type Detection** - Adapt behavior based on agent capabilities
2. **Context-Appropriate Messages** - Send relevant content to each agent
3. **Consistent Interface** - Use same A2A patterns for all agents

## Configuration

The client is configured to connect to these default endpoints:

```csharp
var agents = new[]
{
    new { Name = "Echo Agent", Url = "http://localhost:5001/" },
    new { Name = "Calculator Agent", Url = "http://localhost:5002/" }
};
```

You can modify these URLs to connect to agents running on different ports or hosts.

## Error Handling

The client demonstrates proper error handling:

```csharp
try
{
    await CommunicateWithAgent(agentInfo.Name, agentInfo.Url, agentCard);
}
catch (Exception ex)
{
    Console.WriteLine($"❌ Failed to communicate with {agentInfo.Name}: {ex.Message}");
}
```

Common errors and solutions:
- **Connection refused**: Make sure the agent server is running
- **Timeout**: Check network connectivity and server health
- **Invalid response**: Verify agent is A2A-compatible

## Extending the Client

You can extend this client by:

### 1. Adding More Agents
```csharp
var agents = new[]
{
    new { Name = "Echo Agent", Url = "http://localhost:5001/" },
    new { Name = "Calculator Agent", Url = "http://localhost:5002/" },
    new { Name = "Your Agent", Url = "http://localhost:5003/" }  // Add your agent
};
```

### 2. Interactive Mode
Add user input to send custom messages:
```csharp
Console.Write("Enter message: ");
var userInput = Console.ReadLine();
var message = CreateMessage(userInput);
```

### 3. Task-Based Communication
Use `CreateTaskAsync()` instead of `SendMessageAsync()` for persistent tasks:
```csharp
var task = await client.CreateTaskAsync(new TaskCreateParams { Message = message });
// Monitor task progress, get updates, etc.
```

### 4. Streaming Communication
Use streaming APIs for real-time responses:
```csharp
await foreach (var sseItem in client.SendMessageStreamingAsync(sendParams))
{
    // Process streaming response chunks
}
```

## Next Steps

After understanding the Simple Client:
1. Try modifying the messages sent to agents
2. Add support for additional agent types
3. Implement interactive user input
4. Explore task-based communication patterns
5. Add streaming communication examples

## Common Patterns

This client demonstrates these A2A patterns:
- ✅ Agent discovery and capability querying
- ✅ A2A client creation and configuration
- ✅ Message construction and sending
- ✅ Response processing and display
- ✅ Multi-agent communication
- ✅ Error handling and recovery
