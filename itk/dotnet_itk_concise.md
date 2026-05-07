# Concise .NET SDK ITK Setup Guide

This guide details how to test the `.NET SDK` (`a2a-dotnet`) using the Integration Test Kit (ITK) to mirror the exact same volume mounting structure used by the Python SDK.

For instructions on creating the runner script (`run_tests.sh`) to run ITK tests in a CI/CD pipeline, and how to access debug logs, refer to the [Python SDK reference guide](https://github.com/a2aproject/a2a-python/tree/main/itk).

---

## 📁 Reference `.csproj` Configuration

To allow ITK to correctly detect the `.NET` agent, your executable test project file (`itk/ItkAgent.csproj`) must target `.NET 8.0` and link directly to your `.NET SDK` source code project:

> [!IMPORTANT]
> The `itk/` directory MUST be placed directly at the repository root of `a2a-dotnet` to ensure proper volume mounting structure.

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <!-- Link directly to your local C# SDK project source -->
    <ProjectReference Include="../src/A2A/A2A.csproj" />
  </ItemGroup>
</Project>
```

---

## 🔌 Argument Parsing (`Program.cs`)

The spawner invokes the agent by passing `--httpPort` and `--grpcPort` arguments. The entry point in the C# project must extract these values directly:

```csharp
using System;

class Program
{
    static void Main(string[] args)
    {
        if (args.Length >= 4)
        {
            string httpPort = args[1]; // string directly following --httpPort
            string grpcPort = args[3]; // string directly following --grpcPort

            Console.WriteLine($"ITK Agent active on HTTP port {httpPort} and gRPC port {grpcPort}");
            
            // TODO: Initialize the A2A Server instance using these ports
        }
        Console.ReadLine(); // Keep the process alive
    }
}
```

---

## 🏃 Running Tests via ITK

### 1. Build & Volume Mount Setup

Build the ITK Docker image, and run the container mounting the entire repository root to `/app/agents/repo` and the `itk/` directory to `/app/agents/repo/itk`:

```bash
export A2A_SAMPLES_REVISION=implement-itk-service

# Build the ITK Docker image
docker build -t itk_service .

# Stop any existing container
docker rm -f itk-service || true

# Run the container with full repo mounts
docker run -d --name itk-service \
  -p 8000:8000 \
  -v /path/to/a2a-dotnet:/app/agents/repo \
  -v /path/to/a2a-dotnet/itk:/app/agents/repo/itk \
  itk_service
```

### 2. Submitting Test Scenarios

To test the `.NET` agent against modern (`v1.0`) and legacy (`v0.3`) agents, submit a POST request containing the test definitions:

```bash
curl -s -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "tests": [
      {
        "name": "Dotnet vs Modern (v1.0) - JSONRPC",
        "sdks": ["current", "python_v10", "go_v10"],
        "traversal": "euler",
        "edges": ["0->1", "0->2", "1->0", "2->0"],
        "protocols": ["jsonrpc"],
        "behavior": "send_message"
      },
      {
        "name": "Dotnet vs Legacy (v0.3) - Backwards Compat",
        "sdks": ["current", "python_v03", "go_v03"],
        "traversal": "euler",
        "edges": ["0->1", "0->2", "1->0", "2->0"],
        "protocols": ["jsonrpc"],
        "behavior": "send_message"
      }
    ]
  }'
```
