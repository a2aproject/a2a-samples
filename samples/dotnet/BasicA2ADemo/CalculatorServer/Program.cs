using A2A;
using A2A.AspNetCore;
using CalculatorServer;

var builder = WebApplication.CreateBuilder(args);

// Add logging for better visibility
builder.Logging.AddConsole();

var app = builder.Build();

// Create the task manager - this handles A2A protocol operations
var taskManager = new TaskManager();

// Create and attach the calculator agent
var calculatorAgent = new CalculatorAgent();
calculatorAgent.Attach(taskManager);

// Map the A2A endpoints
app.MapA2A(taskManager, "/");                    // JSON-RPC endpoint

// Add a simple health check
app.MapGet("/health", () => Results.Ok(new
{
    Status = "Healthy",
    Agent = "Calculator Agent",
    Timestamp = DateTimeOffset.UtcNow
}));

// Add a welcome message
app.MapGet("/", () => Results.Ok(new
{
    Message = "Calculator Agent Server is running!",
    Examples = new[] {
        "5 + 3",
        "10 - 4",
        "7 * 8",
        "15 / 3"
    },
    Endpoints = new
    {
        AgentCard = "/.well-known/agent.json",
        A2A = "/ (POST for JSON-RPC)",
        Health = "/health"
    }
}));

Console.WriteLine("🧮 Calculator Agent Server starting...");
Console.WriteLine("🌐 Server will be available at: http://localhost:5002");
Console.WriteLine("📋 Agent card: http://localhost:5002/.well-known/agent.json");
Console.WriteLine("🔍 Health check: http://localhost:5002/health");
Console.WriteLine("💬 Send math expressions via A2A protocol to: http://localhost:5002/");
Console.WriteLine("📝 Example expressions: '5 + 3', '10 * 2', '15 / 3'");

app.Run("http://localhost:5002");
