using A2A;
using A2A.AspNetCore;
using EchoServer;

var builder = WebApplication.CreateBuilder(args);

// Add logging for better visibility
builder.Logging.AddConsole();

var app = builder.Build();

// Create the task manager - this handles A2A protocol operations
var taskManager = new TaskManager();

// Create and attach the echo agent
var echoAgent = new EchoAgent();
echoAgent.Attach(taskManager);

// Map the A2A endpoints
app.MapA2A(taskManager, "/");                    // JSON-RPC endpoint

// Add a simple health check
app.MapGet("/health", () => Results.Ok(new
{
    Status = "Healthy",
    Agent = "Echo Agent",
    Timestamp = DateTimeOffset.UtcNow
}));

// Add a welcome message
app.MapGet("/", () => Results.Ok(new
{
    Message = "Echo Agent Server is running!",
    Endpoints = new
    {
        AgentCard = "/.well-known/agent.json",
        A2A = "/ (POST for JSON-RPC)",
        Health = "/health"
    }
}));

Console.WriteLine("🔊 Echo Agent Server starting...");
Console.WriteLine("🌐 Server will be available at: http://localhost:5001");
Console.WriteLine("📋 Agent card: http://localhost:5001/.well-known/agent.json");
Console.WriteLine("🔍 Health check: http://localhost:5001/health");
Console.WriteLine("💬 Send messages via A2A protocol to: http://localhost:5001/");

app.Run("http://localhost:5001");
