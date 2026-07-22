using A2A;
using System.Diagnostics;
using System.Text.Json;
using System.Runtime.InteropServices;

namespace CLIServer;

/// <summary>
/// Represents the result of a command execution with all relevant details.
/// </summary>
/// <param name="Command">The full command that was executed</param>
/// <param name="ExitCode">The exit code returned by the process</param>
/// <param name="Output">The standard output lines from the command</param>
/// <param name="Errors">The standard error lines from the command</param>
/// <param name="Success">Whether the command executed successfully (exit code 0)</param>
internal record CommandExecutionResult(
    string Command,
    int ExitCode,
    IReadOnlyList<string> Output,
    IReadOnlyList<string> Errors,
    bool Success);

/// <summary>
/// A CLI agent that can execute command-line tools and return results.
/// This demonstrates how to bridge AI agents with system-level operations.
/// 
/// IMPORTANT: This sample should NOT be exposed to untrusted clients.
/// The command bridge runs local system commands and is intended for
/// development and trusted environments only.
/// </summary>
public class CLIAgent
{
    /// <summary>
    /// Allowed commands — safe, read-only system utilities.
    /// Interpreters and package managers (python, node, npm, dotnet) are
    /// intentionally excluded: they accept arbitrary code as arguments,
    /// which cannot be meaningfully constrained by an allowlist.
    /// </summary>
    private static readonly HashSet<string> AllowedCommands = new()
    {
        // Safe read-only commands
        "dir", "ls", "pwd", "whoami", "date", "time",
        "echo", "cat", "type", "head", "tail",
        "ps", "tasklist", "netstat", "ipconfig", "ping",
        "git"
    };

    /// <summary>
    /// Gets the list of allowed commands that this agent can execute.
    /// </summary>
    public IReadOnlyCollection<string> GetAllowedCommands() => AllowedCommands;

    public void Attach(ITaskManager taskManager)
    {
        taskManager.OnMessageReceived = ProcessMessageAsync;
        taskManager.OnAgentCardQuery = GetAgentCardAsync;
    }

    /// <summary>
    /// Processes incoming messages and executes CLI commands safely.
    /// </summary>
    private async Task<Message> ProcessMessageAsync(MessageSendParams messageSendParams, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            throw new OperationCanceledException(cancellationToken);
        }

        var userText = GetTextFromMessage(messageSendParams.Message);
        Console.WriteLine($"[CLI Agent] Received command: {userText}");

        try
        {
            // Parse the command
            var commandResult = await ExecuteCommandAsync(userText, cancellationToken);

            var responseMessage = new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = commandResult }]
            };

            Console.WriteLine($"[CLI Agent] Command executed successfully");
            return responseMessage;
        }
        catch (Exception ex)
        {
            var errorText = $"Error executing command '{userText}': {ex.Message}";

            var errorMessage = new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = errorText }]
            };

            Console.WriteLine($"[CLI Agent] Error: {ex.Message}");
            return errorMessage;
        }
    }

    /// <summary>
    /// Executes a CLI command safely with security checks.
    /// Uses direct process invocation (no shell) — the command runs as the
    /// executable and arguments are passed as an argv array. This prevents
    /// shell metacharacter injection (;, |, &amp;&amp;, $(), backticks).
    /// </summary>
    private async Task<string> ExecuteCommandAsync(string input, CancellationToken cancellationToken)
    {
        // Parse command and arguments into a list
        var parts = ParseCommand(input);
        var command = parts.Command;
        var argumentList = parts.Arguments;

        // Security check: Only allow whitelisted commands
        if (!IsCommandAllowed(command))
        {
            return $"❌ Command '{command}' is not allowed for security reasons.\n" +
                   $"Allowed commands: {string.Join(", ", AllowedCommands)}";
        }

        // Execute the command directly — no shell, no /bin/bash -c, no cmd /c
        using var process = new Process();

        process.StartInfo.FileName = command;
        process.StartInfo.UseShellExecute = false;
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.RedirectStandardError = true;
        process.StartInfo.CreateNoWindow = true;

        // Pass arguments as a proper argv array. ArgumentList handles
        // platform-specific quoting and never invokes a shell, so
        // metacharacters arrive as literal argv entries.
        foreach (var arg in argumentList)
        {
            process.StartInfo.ArgumentList.Add(arg);
        }

        var output = new List<string>();
        var errors = new List<string>();

        // Capture output and errors
        process.OutputDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                output.Add(e.Data);
        };

        process.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                errors.Add(e.Data);
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        // Wait for completion with timeout
        await process.WaitForExitAsync(cancellationToken);

        var result = new CommandExecutionResult(
            Command: $"{command} {string.Join(" ", argumentList)}",
            ExitCode: process.ExitCode,
            Output: output.AsReadOnly(),
            Errors: errors.AsReadOnly(),
            Success: process.ExitCode == 0
        );

        return FormatCommandResult(result);
    }

    /// <summary>
    /// Parses user input into a command name and an argument list.
    /// Arguments are returned as individual tokens — never interpolated
    /// into a shell command string.
    /// </summary>
    private static (string Command, List<string> Arguments) ParseCommand(string input)
    {
        var trimmed = input.Trim();
        var spaceIndex = trimmed.IndexOf(' ');

        if (spaceIndex == -1)
        {
            return (trimmed, new List<string>());
        }

        var command = trimmed.Substring(0, spaceIndex);
        var argsString = trimmed.Substring(spaceIndex + 1);

        // Split remaining text into individual argument tokens.
        // Simple whitespace split is sufficient for the sample's
        // read-only, non-shell command set.
        var args = argsString
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .ToList();

        return (command, args);
    }

    /// <summary>
    /// Security check: Ensures only safe commands are executed.
    /// </summary>
    private static bool IsCommandAllowed(string command)
    {
        return AllowedCommands.Contains(command.ToLowerInvariant());
    }

    /// <summary>
    /// Formats the command execution result in a user-friendly way.
    /// </summary>
    private static string FormatCommandResult(CommandExecutionResult result)
    {
        var output = new List<string>();

        output.Add($"🖥️ Command: {result.Command}");
        output.Add($"✅ Exit Code: {result.ExitCode}");

        if (result.Output.Count > 0)
        {
            output.Add("\n📤 Output:");
            foreach (string line in result.Output)
            {
                output.Add($"  {line}");
            }
        }

        if (result.Errors.Count > 0)
        {
            output.Add("\n❌ Errors:");
            foreach (string line in result.Errors)
            {
                output.Add($"  {line}");
            }
        }

        if (result.Output.Count == 0 && result.Errors.Count == 0)
        {
            output.Add("\n✅ Command completed successfully (no output)");
        }

        return string.Join("\n", output);
    }

    /// <summary>
    /// Retrieves the agent card information for the CLI Agent.
    /// </summary>
    private Task<AgentCard> GetAgentCardAsync(string agentUrl, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<AgentCard>(cancellationToken);
        }

        return Task.FromResult(new AgentCard
        {
            Name = "CLI Agent",
            Description = "Executes command-line tools safely. Supports common commands like 'dir', 'ls', 'git status', 'dotnet build', etc.",
            Url = agentUrl,
            Version = "1.0.0",
            DefaultInputModes = ["text"],
            DefaultOutputModes = ["text"],
            Capabilities = new AgentCapabilities { Streaming = true }
        });
    }

    /// <summary>
    /// Helper method to extract text from a message.
    /// </summary>
    private static string GetTextFromMessage(Message message)
    {
        return message.Parts?.OfType<TextPart>().FirstOrDefault()?.Text ?? string.Empty;
    }
}
