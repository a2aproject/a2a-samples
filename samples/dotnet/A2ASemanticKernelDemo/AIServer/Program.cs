using A2A;
using A2A.AspNetCore;
using AIServer;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;

var builder = WebApplication.CreateBuilder(args);

// Add logging for better visibility
builder.Logging.AddConsole();

// Configure Semantic Kernel
builder.Services.AddKernel();

// Configure AI model (you'll need to set up your preferred AI service)
// For Azure OpenAI:
// builder.Services.AddAzureOpenAIChatCompletion(
//     deploymentName: "your-deployment-name",
//     endpoint: "your-azure-openai-endpoint",
//     apiKey: "your-api-key");

// For OpenAI:
// builder.Services.AddOpenAIChatCompletion(
//     modelId: "gpt-3.5-turbo",
//     apiKey: "your-openai-api-key");

// For development/testing, you can use a mock service
builder.Services.AddSingleton<IChatCompletionService>(provider =>
{
    // This is a simple mock for demonstration - replace with real AI service
    return new MockChatCompletionService();
});

// Register the AI Agent
builder.Services.AddSingleton<AIAgent>();

var app = builder.Build();

// Create the task manager - this handles A2A protocol operations
var taskManager = new TaskManager();

// Create and attach the AI agent
var aiAgent = app.Services.GetRequiredService<AIAgent>();
aiAgent.Attach(taskManager);

// Map the A2A endpoints
app.MapA2A(taskManager, "/");                    // JSON-RPC endpoint

app.Run();

/// <summary>
/// Mock chat completion service for demonstration purposes
/// Replace this with a real AI service in production
/// </summary>
public class MockChatCompletionService : IChatCompletionService
{
    public IReadOnlyDictionary<string, object?> Attributes { get; } = new Dictionary<string, object?>();

    public Task<IReadOnlyList<ChatMessageContent>> GetChatMessageContentsAsync(
        ChatHistory chatHistory,
        PromptExecutionSettings? executionSettings = null,
        Kernel? kernel = null,
        CancellationToken cancellationToken = default)
    {
        // Simple mock responses based on prompt content
        var lastMessage = chatHistory.LastOrDefault()?.Content ?? "";

        string response = lastMessage.ToLower() switch
        {
            var msg when msg.Contains("summarize") => "This is a brief summary of the provided text with key points highlighted.",
            var msg when msg.Contains("sentiment") => """{"sentiment": "Positive", "confidence": 75, "emotions": ["optimism", "enthusiasm"], "explanation": "The text shows generally positive sentiment with optimistic language."}""",
            var msg when msg.Contains("translate") => "Ceci est la traduction française du texte fourni.",
            var msg when msg.Contains("ideas") =>
"""
- **Digital Innovation**: Leverage technology to create new solutions
- **Sustainable Practices**: Implement eco-friendly approaches
- **Community Engagement**: Build stronger connections with stakeholders
- **Creative Collaboration**: Foster cross-functional teamwork
- **Data-Driven Insights**: Use analytics to guide decision making
""",
            _ => "I'm a mock AI service. Please configure a real AI provider (Azure OpenAI, OpenAI, etc.) for full functionality."
        };

        var result = new List<ChatMessageContent>
        {
            new(AuthorRole.Assistant, response)
        };

        return Task.FromResult<IReadOnlyList<ChatMessageContent>>(result);
    }

    public async IAsyncEnumerable<StreamingChatMessageContent> GetStreamingChatMessageContentsAsync(
        ChatHistory chatHistory,
        PromptExecutionSettings? executionSettings = null,
        Kernel? kernel = null,
        CancellationToken cancellationToken = default)
    {
        var messages = await GetChatMessageContentsAsync(chatHistory, executionSettings, kernel, cancellationToken);
        foreach (var message in messages)
        {
            yield return new StreamingChatMessageContent(message.Role, message.Content);
        }
    }
}
