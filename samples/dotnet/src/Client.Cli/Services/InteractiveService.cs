namespace GitHubAgentCli.Services;

public static class InteractiveService
{
    public static async Task RunSessionAsync(string baseUrl, string mode)
    {
        Console.WriteLine("GitHub Agent Interactive Session");
        Console.WriteLine("══════════════════════════════");
        Console.WriteLine($"Mode: {mode.ToUpper()}");
        Console.WriteLine($"Server: {baseUrl}");
        Console.WriteLine("Commands: 'help', 'status', 'tools', 'switch', 'quit'");
        Console.WriteLine();

        bool continueSession = true;
        string currentMode = mode.ToLower();

        while (continueSession)
        {
            Console.Write($"[{currentMode}] github-agent> ");
            string? input = Console.ReadLine()?.Trim();

            if (string.IsNullOrEmpty(input))
            {
                continue;
            }

            switch (input.ToLower())
            {
                case "quit" or ":q":
                    continueSession = false;
                    break;
                case "help":
                    ShowHelp();
                    break;
                case "status":
                    await ApiService.GetStatusAsync(baseUrl);
                    break;
                case "tools":
                    await ApiService.GetAvailableToolsAsync(baseUrl);
                    break;
                case "switch":
                    currentMode = currentMode == "a2a" ? "api" : "a2a";
                    Console.WriteLine($"Switched to {currentMode.ToUpper()} mode");
                    break;
                default:
                    if (currentMode == "api")
                    {
                        await ApiService.RunQueryAsync(baseUrl, input);
                    }
                    else
                    {
                        Console.WriteLine("A2A interactive mode - use 'github-agent-cli a2a' for full A2A experience");
                    }
                    break;
            }

            Console.WriteLine();
        }
    }

    private static void ShowHelp()
    {
        Console.WriteLine();
        Console.WriteLine("Interactive Commands:");
        Console.WriteLine("────────────────────");
        Console.WriteLine("  help     - Show this help");
        Console.WriteLine("  status   - Get agent status");
        Console.WriteLine("  tools    - List available tools");
        Console.WriteLine("  switch   - Switch between A2A and API modes");
        Console.WriteLine("  quit     - Exit session");
        Console.WriteLine();
        Console.WriteLine("Example GitHub Queries:");
        Console.WriteLine("─────────────────────");
        Console.WriteLine("  • What repositories does microsoft have?");
        Console.WriteLine("  • Show me the latest commits in microsoft/semantic-kernel");
        Console.WriteLine("  • What are the open issues in facebook/react?");
        Console.WriteLine("  • Get the README for tensorflow/tensorflow");
        Console.WriteLine();
    }
}