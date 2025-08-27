using A2A;
using A2A.AspNetCore;
using CLIServer;

var builder = WebApplication.CreateBuilder(args);

// Add logging for better visibility
builder.Logging.AddConsole();
builder.Logging.SetMinimumLevel(LogLevel.Information);

var app = builder.Build();

// Create the task manager
var taskManager = new TaskManager();

// Create and attach the CLI agent
var cliAgent = new CLIAgent();
cliAgent.Attach(taskManager);

// Map the A2A endpoints
app.MapA2A(taskManager, "/");                    // JSON-RPC endpoint

// Add a simple health check
app.MapGet("/health", () => Results.Ok(new
{
    Status = "Healthy",
    Agent = "CLI Agent",
    Timestamp = DateTimeOffset.UtcNow,
    AllowedCommands = cliAgent.GetAllowedCommands()
}));

// Add a welcome message
app.MapGet("/", () => Results.Ok(new
{
    Message = "🖥️ CLI Agent is running!",
    Description = "Send CLI commands like 'dir', 'ls', 'git status', 'dotnet --version'",
    Endpoint = "/",
    Health = "/health"
}));

Console.WriteLine("🖥️ CLI Agent starting...");
Console.WriteLine("📍 Available at: http://localhost:5003");
Console.WriteLine($"🔧 Allowed commands: {string.Join(", ", cliAgent.GetAllowedCommands())}");
Console.WriteLine("⚠️  Security: Only whitelisted commands are allowed");

app.Run("http://localhost:5003");
