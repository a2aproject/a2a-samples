# Calculator Server

A basic calculator A2A agent that performs arithmetic operations. This demonstrates how to implement business logic and input validation in an A2A agent.

## What This Agent Does

The Calculator Agent can:
- Parse simple math expressions like "5 + 3" or "10.5 * 2"
- Perform basic arithmetic operations: `+`, `-`, `*`, `/`
- Handle decimal numbers
- Provide helpful error messages for invalid expressions
- Demonstrate input validation and error handling

## Key Files

- **`CalculatorAgent.cs`** - The calculator agent implementation with math logic
- **`Program.cs`** - ASP.NET Core server setup
- **`CalculatorServer.csproj`** - Project configuration

## Running the Calculator Server

```bash
cd CalculatorServer
dotnet run
```

The server will start on `http://localhost:5002`

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Welcome message with example expressions |
| `/` | POST | A2A JSON-RPC communication endpoint |
| `/.well-known/agent.json` | GET | Agent discovery (agent card) |
| `/health` | GET | Health check |

## Supported Operations

| Operation | Example | Result |
|-----------|---------|--------|
| Addition | `5 + 3` | `5 + 3 = 8` |
| Subtraction | `10 - 4` | `10 - 4 = 6` |
| Multiplication | `7 * 8` | `7 * 8 = 56` |
| Division | `15 / 3` | `15 / 3 = 5` |
| Decimals | `2.5 + 1.7` | `2.5 + 1.7 = 4.2` |

## Testing the Agent

### 1. Check if it's running
```bash
curl http://localhost:5002/health
```

### 2. Get the agent card
```bash
curl http://localhost:5002/.well-known/agent.json
```

### 3. Send math expressions
Use the SimpleClient project or any A2A-compatible client to send expressions like:
- "5 + 3"
- "10.5 * 2"
- "15 / 3"

## Learning Points

### Business Logic Implementation

```csharp
public Task<AgentResponse> OnMessageAsync(Message message, CancellationToken cancellationToken)
{
    var userText = GetTextFromMessage(message);
    
    try
    {
        // Parse and evaluate the math expression
        var result = EvaluateExpression(userText);
        var responseText = $"{userText} = {result}";
        
        // Create success response
        return CreateResponse(responseText);
    }
    catch (Exception ex)
    {
        // Handle errors gracefully
        var errorText = $"Sorry, I couldn't calculate '{userText}'. Error: {ex.Message}";
        return CreateResponse(errorText);
    }
}
```

### Input Validation with Regex

```csharp
private static double EvaluateExpression(string expression)
{
    // Parse expressions like "5 + 3" or "10.5 * 2"
    var pattern = @"^\s*(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)\s*$";
    var match = Regex.Match(expression, pattern);
    
    if (!match.Success)
    {
        throw new ArgumentException("Please use format like '5 + 3'");
    }
    
    // Extract operands and operation
    var leftOperand = double.Parse(match.Groups[1].Value);
    var operation = match.Groups[2].Value;
    var rightOperand = double.Parse(match.Groups[3].Value);
    
    // Perform calculation
    return operation switch
    {
        "+" => leftOperand + rightOperand,
        "-" => leftOperand - rightOperand,
        "*" => leftOperand * rightOperand,
        "/" => rightOperand == 0 ? throw new DivideByZeroException() : leftOperand / rightOperand,
        _ => throw new ArgumentException($"Unsupported operation: {operation}")
    };
}
```

### Agent Capabilities Declaration

```csharp
public Task<AgentCard> OnAgentCardQuery(string agentUrl, CancellationToken cancellationToken)
{
    var agentCard = new AgentCard
    {
        Name = Name,
        Description = Description,
        Capabilities = [
            new AgentCapability
            {
                Id = "calculate",
                Name = "Basic Math Operations",
                Description = "Performs basic arithmetic operations",
                Examples = [
                    "5 + 3",
                    "10 - 4", 
                    "7 * 8",
                    "15 / 3"
                ],
                InputModes = ["text/plain"],
                OutputModes = ["text/plain"]
            }
        ]
    };
    return Task.FromResult(agentCard);
}
```

## Key Concepts Demonstrated

1. **Input Validation** - Using regex to parse and validate user input
2. **Error Handling** - Graceful handling of invalid expressions and division by zero
3. **Business Logic** - Implementing domain-specific functionality (math operations)
4. **Capability Declaration** - Describing what the agent can do with examples
5. **User-Friendly Responses** - Providing helpful error messages

## Error Handling Examples

The agent handles various error cases:

| Input | Response |
|-------|----------|
| `"hello"` | `"Sorry, I couldn't calculate 'hello'. Please use format like '5 + 3'"` |
| `"5 / 0"` | `"Sorry, I couldn't calculate '5 / 0'. Error: Cannot divide by zero"` |
| `"5 % 3"` | `"Sorry, I couldn't calculate '5 % 3'. Error: Unsupported operation: %"` |

## Extending the Calculator

You can extend this agent by:
1. Adding more operations (%, ^, sqrt, etc.)
2. Supporting more complex expressions (parentheses, multiple operations)
3. Adding memory functions (store, recall)
4. Supporting different number bases (binary, hex)
5. Adding trigonometric functions

## Next Steps

After understanding the Calculator Agent:
1. Compare with the **EchoServer** to see the difference in complexity
2. Examine the **SimpleClient** to see how it sends different types of messages
3. Try adding new mathematical operations
4. Implement more sophisticated expression parsing

## Common Patterns

This agent demonstrates these A2A patterns:
- ✅ Input validation and parsing
- ✅ Business logic implementation  
- ✅ Error handling and user feedback
- ✅ Capability documentation with examples
- ✅ Domain-specific agent functionality
