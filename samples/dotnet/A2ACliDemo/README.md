# CLI Agent Demo

This demo shows how to build an A2A agent that can execute command-line tools safely. It demonstrates bridging AI agents with system-level operations.

## What's Included

- **CLIServer**: An agent that executes CLI commands with security restrictions
- **CLIClient**: An interactive console client that sends commands to the agent

## Key Features

### 🔒 Security First
- **Whitelist approach**: Only safe commands are allowed
- **No dangerous operations**: Commands like `rm`, `del`, `format` are blocked
- **Input validation**: All commands are parsed and validated

### 🖥️ Cross-Platform Support
- **Windows**: Executes real Windows executables directly (`whoami`, `tasklist`, `ipconfig`, ...)
- **Linux/Mac**: Executes real Unix binaries directly (`ls`, `pwd`, `cat`, `ps`, ...)
- **No shell**: Commands run via direct process invocation (`UseShellExecute = false`), never through `cmd.exe` or `/bin/bash` — arguments are passed as an argv array, so shell metacharacters arrive as literal text

### 📊 Rich Output
- **Structured results**: Shows command, exit code, output, and errors
- **Real-time feedback**: Displays execution status
- **Error handling**: Graceful handling of failed commands

## Getting Started

### Option 1: Quick Start (Windows)
```bash
run-demo.bat
```

### Option 2: Manual Setup

#### 1. Start the CLI Agent Server
```bash
cd CLIServer
dotnet run
```
The server will start on `http://localhost:5003`

#### 2. Run the Interactive Client
```bash
cd CLIClient
dotnet run
```

## Example Commands

### File Operations
```bash
CLI> ls -la                 # List directory with details (Linux/Mac)
CLI> pwd                    # Show current directory
CLI> cat README.md          # Show file contents
```

### System Information
```bash
CLI> whoami                 # Show current user
CLI> ps                     # List processes (Linux/Mac)
CLI> tasklist               # List processes (Windows)
```

### Development Tools
```bash
CLI> git status             # Check git repository status
```

### Network Commands
```bash
CLI> ping google.com        # Test network connectivity
CLI> ipconfig               # Show network configuration (Windows)
CLI> netstat                # Show network connections
```

## Security Considerations

### Allowed Commands
The agent only allows these commands — real executables only; shell builtins and interpreters are excluded:
- **File operations**: `ls`, `pwd`, `cat`, `head`, `tail`
- **System info**: `whoami`
- **Process info**: `ps`, `tasklist`
- **Network**: `ping`, `ipconfig`, `netstat`
- **Development tools**: `git`

### Blocked Commands
Dangerous commands are blocked for security:
- File deletion: `rm`, `del`, `rmdir`
- System modification: `format`, `fdisk`, `sudo`
- Process control: `kill`, `killall`

### Best Practices
1. **Run with limited privileges**: Don't run as administrator/root
2. **Network isolation**: Consider running in a sandboxed environment
3. **Audit logging**: Monitor command execution in production
4. **Regular updates**: Keep the whitelist updated as needed

## Project Structure

```text
CLIAgent/
├── README.md                    # This file
├── CLIServer/
│   ├── CLIServer.csproj        # Server project file
│   ├── Program.cs              # Server startup code
│   └── CLIAgent.cs             # CLI agent implementation
└── CLIClient/
    ├── CLIClient.csproj        # Client project file
    └── Program.cs              # Interactive client implementation
```

## Extending the Agent

### Adding New Commands
1. Add the command to the `AllowedCommands` set in `CLIAgent.cs`
2. Test thoroughly to ensure security
3. Update documentation

### Custom Command Handlers
You can add special handling for specific commands:

```csharp
private async Task<string> ExecuteCommandAsync(string input, CancellationToken cancellationToken)
{
    // Special handling for specific commands
    if (input.StartsWith("git"))
    {
        return await ExecuteGitCommand(input, cancellationToken);
    }
    
    // Default command execution
    return await ExecuteGenericCommand(input, cancellationToken);
}
```

### Output Formatting
Customize how results are presented:

```csharp
private static string FormatCommandResult(dynamic result)
{
    // Custom formatting based on command type
    // Add JSON output, markdown formatting, etc.
}
```

This demo provides a foundation for understanding how to safely integrate system-level operations with A2A agents while maintaining security and usability.
