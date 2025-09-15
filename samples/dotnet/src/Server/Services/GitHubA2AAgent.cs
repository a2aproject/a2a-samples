using A2A;
using Github;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;
using ModelContextProtocol.Client;

namespace Server.Services;

public class GitHubA2AAgent(
    ILogger<GitHubA2AAgent> logger,
    ToolService toolService,
    AgentService agentService)
{
    private IList<McpClientTool>? _tools;

    public bool IsInitialized { get; private set; }
    public DateTime? InitializedAt { get; private set; }

    public async Task InitializeAsync()
    {
        try
        {
            logger.LogInformation("Initializing GitHub A2A Agent...");

            _tools = await toolService.GetGithubTools();
            logger.LogInformation($"Retrieved {_tools.Count} GitHub tools");

            IsInitialized = true;
            InitializedAt = DateTime.UtcNow;

            logger.LogInformation("GitHub A2A Agent initialized successfully");
        }
        catch (Exception ex)
        {
            IsInitialized = false;
            InitializedAt = null;
            logger.LogError(ex, "Failed to initialize GitHub A2A Agent");
            throw;
        }
    }

    public void Attach(ITaskManager taskManager)
    {
        if (!IsInitialized)
        {
            throw new InvalidOperationException("Agent must be initialized before attaching to task manager");
        }

        taskManager.OnMessageReceived = ProcessMessageAsync;
        taskManager.OnAgentCardQuery = GetAgentCardAsync;

        logger.LogInformation("GitHub A2A Agent attached to task manager");
    }

    public async Task<string> ProcessDirectQueryAsync(string query)
    {
        if (!IsInitialized)
        {
            throw new InvalidOperationException("Agent is not initialized");
        }

        logger.LogInformation("Processing direct query: {Query}", query);

        ChatMessageContent response = await agentService.ProcessQuery(query, CancellationToken.None);
        return response.Content ?? "No response generated";
    }

    public async Task<IList<McpClientTool>> GetAvailableToolsAsync()
    {
        if (!IsInitialized || _tools == null)
        {
            throw new InvalidOperationException("Agent is not initialized");
        }

        return _tools;
    }

    private async Task<Message> ProcessMessageAsync(MessageSendParams messageSendParams, CancellationToken cancellationToken)
    {
        try
        {
            logger.LogInformation("Processing A2A message: {MessageId}", messageSendParams.Message.MessageId);

            if (!IsInitialized)
            {
                throw new InvalidOperationException("Agent service is not initialized");
            }

            TextPart? textPart = messageSendParams.Message.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart == null)
            {
                return CreateErrorMessage(messageSendParams.Message, "No text content found in message");
            }

            string query = textPart.Text;
            logger.LogInformation("Processing query: {Query}", query);

            ChatMessageContent response = await agentService.ProcessQuery(query, cancellationToken);

            Message responseMessage = new()
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = response.Content ?? "No response generated" }]
            };

            logger.LogInformation("Successfully processed A2A message: {MessageId}", messageSendParams.Message.MessageId);
            return responseMessage;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error processing A2A message: {MessageId}", messageSendParams.Message.MessageId);
            return CreateErrorMessage(messageSendParams.Message, $"Error processing request: {ex.Message}");
        }
    }

    private Task<AgentCard> GetAgentCardAsync(string agentUrl, CancellationToken cancellationToken)
    {
        string[] toolNames = _tools?.Select(t => t.Name).ToArray() ?? Array.Empty<string>();

        string detailedDescription = $"An intelligent agent that can answer questions about GitHub repositories using the Model Context Protocol (MCP) and Semantic Kernel. " +
                                     $"Available tools: {string.Join(", ", toolNames.Take(5))}{(toolNames.Length > 5 ? "..." : "")}. " +
                                     $"Capabilities include repository analysis, code exploration, issue tracking, pull request analysis, and general GitHub queries. " +
                                     $"Powered by {Environment.GetEnvironmentVariable("OPENAI_MODEL_NAME") ?? "gpt-4o-mini"} via Semantic Kernel.";

        AgentCard card = new()
        {
            Name = "GitHub Agent",
            Description = detailedDescription,
            Url = agentUrl,
            Version = "1.0.0",
            DefaultInputModes = ["text"],
            DefaultOutputModes = ["text"],
            Capabilities = new AgentCapabilities
            {
                Streaming = false
            }
        };

        return Task.FromResult(card);
    }

    private static Message CreateErrorMessage(Message originalMessage, string errorText)
    {
        return new Message
        {
            Role = MessageRole.Agent,
            MessageId = Guid.NewGuid().ToString(),
            ContextId = originalMessage.ContextId,
            Parts = [new TextPart { Text = errorText }]
        };
    }
}