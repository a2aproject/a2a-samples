using A2A;
using System.Text.Json;

namespace CLIClient;

/// <summary>
/// Interactive CLI client that demonstrates how to send commands to the CLI Agent.
/// This shows how clients can interact with specialized agents.
/// </summary>
internal static class Program
{
    private static readonly string AgentUrl = "http://localhost:5003";

    static async Task Main(string[] args)
    {
        Console.WriteLine("🖥️ CLI Agent Client");
        Console.WriteLine("==================");
        Console.WriteLine();

        try
        {
            // Test connection and get agent info
            await TestAgentConnection();

            // Start interactive session
            await StartInteractiveSession();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
            Console.WriteLine();
            Console.WriteLine("Make sure the CLI Agent server is running on http://localhost:5003");
            Console.WriteLine("Start it with: cd CLIServer && dotnet run");
        }
    }

    /// <summary>
    /// Tests the connection to the CLI Agent and displays its capabilities.
    /// </summary>
    private static async Task TestAgentConnection()
    {
        Console.WriteLine("🔍 Connecting to CLI Agent...");

        // Create agent card resolver
        var agentCardResolver = new A2ACardResolver(new Uri(AgentUrl));

        // Get agent card to verify connection
        var agentCard = await agentCardResolver.GetAgentCardAsync();

        Console.WriteLine($"✅ Connected to: {agentCard.Name}");
        Console.WriteLine($"   📝 Description: {agentCard.Description}");
        Console.WriteLine($"   🔢 Version: {agentCard.Version}");
        Console.WriteLine($"   🎯 Streaming: {agentCard.Capabilities?.Streaming}");
        Console.WriteLine();
    }

    /// <summary>
    /// Starts an interactive session where users can send commands to the agent.
    /// </summary>
    private static async Task StartInteractiveSession()
    {
        var agentClient = new A2AClient(new Uri(AgentUrl));

        Console.WriteLine("🚀 Interactive CLI Session Started!");
        Console.WriteLine("Type commands to execute on the agent (e.g., 'dir', 'git status', 'dotnet --version')");
        Console.WriteLine("Type 'help' for examples, 'exit' to quit");
        Console.WriteLine();

        while (true)
        {
            // Get user input
            Console.Write("CLI> ");
            var input = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(input))
                continue;

            // Handle special commands
            switch (input.ToLower())
            {
                case "exit" or "quit":
                    Console.WriteLine("👋 Goodbye!");
                    return;

                case "help":
                    ShowHelp();
                    continue;

                case "examples":
                    await RunExamples(agentClient);
                    continue;

                default:
                    // Send command to agent
                    await ExecuteCommand(agentClient, input);
                    break;
            }
        }
    }

    /// <summary>
    /// Executes a single command through the CLI Agent.
    /// </summary>
    private static async Task ExecuteCommand(A2AClient agentClient, string command)
    {
        try
        {
            Console.WriteLine($"⏳ Executing: {command}");
            Console.WriteLine();

            // Create the message
            var message = new Message
            {
                Role = MessageRole.User,
                MessageId = Guid.NewGuid().ToString(),
                Parts = [new TextPart { Text = command }]
            };

            // Send to agent and get response
            var response = await agentClient.SendMessageAsync(new MessageSendParams { Message = message });

            if (response is Message responseMessage)
            {
                var responseText = responseMessage.Parts?.OfType<TextPart>().FirstOrDefault()?.Text ?? "No response";
                Console.WriteLine(responseText);
            }
            else
            {
                Console.WriteLine("❌ Unexpected response type");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error executing command: {ex.Message}");
        }

        Console.WriteLine();
    }

    /// <summary>
    /// Shows help information with available commands and examples.
    /// </summary>
    private static void ShowHelp()
    {
        Console.WriteLine("📚 CLI Agent Help");
        Console.WriteLine("=================");
        Console.WriteLine();
        Console.WriteLine("🔧 Available Commands:");
        Console.WriteLine("  • File operations: dir, ls, pwd, cat, type");
        Console.WriteLine("  • System info: whoami, date, time");
        Console.WriteLine("  • Process info: ps, tasklist");
        Console.WriteLine("  • Network: ping, ipconfig, netstat");
        Console.WriteLine("  • Development: git, dotnet, node, npm, python");
        Console.WriteLine();
        Console.WriteLine("💡 Example Commands:");
        Console.WriteLine("  • dir              - List current directory (Windows)");
        Console.WriteLine("  • ls -la           - List directory with details (Linux/Mac)");
        Console.WriteLine("  • git status       - Check git repository status");
        Console.WriteLine("  • dotnet --version - Check .NET version");
        Console.WriteLine("  • ping google.com  - Test network connectivity");
        Console.WriteLine();
        Console.WriteLine("🎮 Special Commands:");
        Console.WriteLine("  • help     - Show this help");
        Console.WriteLine("  • examples - Run pre-defined examples");
        Console.WriteLine("  • exit     - Quit the application");
        Console.WriteLine();
    }

    /// <summary>
    /// Runs a series of example commands to demonstrate the CLI Agent's capabilities.
    /// </summary>
    private static async Task RunExamples(A2AClient agentClient)
    {
        Console.WriteLine("🎯 Running Example Commands");
        Console.WriteLine("============================");
        Console.WriteLine();

        var examples = new[]
        {
            "whoami",           // Show current user
            "date",             // Show current date
            "dotnet --version", // Check .NET version
            "git --version",    // Check Git version (if available)
            System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(
                System.Runtime.InteropServices.OSPlatform.Windows) ? "dir" : "ls"  // List directory
        };

        foreach (var example in examples)
        {
            await ExecuteCommand(agentClient, example);

            // Small delay between commands for better readability
            await Task.Delay(1000);
        }

        Console.WriteLine("✅ Examples completed!");
        Console.WriteLine();
    }
}
