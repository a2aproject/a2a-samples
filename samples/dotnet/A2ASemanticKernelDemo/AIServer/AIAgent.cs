using A2A;
using A2A.AspNetCore;
using Microsoft.SemanticKernel;
using System.ComponentModel;
using System.Text.Json;

namespace AIServer;

/// <summary>
/// AI Agent that uses Semantic Kernel for intelligent text processing and analysis
/// </summary>
public class AIAgent
{
    private readonly Kernel _kernel;
    private readonly ILogger<AIAgent> _logger;

    public AIAgent(Kernel kernel, ILogger<AIAgent> logger)
    {
        _kernel = kernel;
        _logger = logger;
    }

    public void Attach(ITaskManager taskManager)
    {
        taskManager.OnMessageReceived = ProcessMessageAsync;
        taskManager.OnAgentCardQuery = GetAgentCardAsync;
    }

    /// <summary>
    /// Handles incoming messages and routes them to the appropriate AI function
    /// </summary>
    private async Task<Message> ProcessMessageAsync(MessageSendParams messageSendParams, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            throw new OperationCanceledException(cancellationToken);
        }

        var userText = GetTextFromMessage(messageSendParams.Message);
        _logger.LogInformation("Processing AI request: {UserText}", userText);

        try
        {
            // Parse the command - for now we'll use simple text parsing
            // In production, you'd want more sophisticated parsing
            var lowerText = userText.ToLower();

            if (lowerText.StartsWith("summarize:"))
            {
                var text = userText.Substring(userText.IndexOf(':') + 1).Trim();
                return await SummarizeTextAsync(text);
            }
            else if (lowerText.StartsWith("sentiment:"))
            {
                var text = userText.Substring(userText.IndexOf(':') + 1).Trim();
                return await AnalyzeSentimentAsync(text);
            }
            else if (lowerText.StartsWith("ideas:"))
            {
                var topic = userText.Substring(userText.IndexOf(':') + 1).Trim();
                return await GenerateIdeasAsync(topic);
            }
            else if (lowerText.StartsWith("translate:"))
            {
                var text = userText.Substring(userText.IndexOf(':') + 1).Trim();
                return await TranslateTextAsync(text, "Spanish"); // Default target language
            }
            else if (lowerText.Contains("help"))
            {
                return await GetCapabilitiesAsync();
            }
            else
            {
                return await GetCapabilitiesAsync();
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing AI request");
            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = $"Error processing request: {ex.Message}" }]
            };
        }
    }

    /// <summary>
    /// Extracts text content from a message
    /// </summary>
    private string GetTextFromMessage(Message message)
    {
        if (message.Parts?.Any() == true)
        {
            foreach (var part in message.Parts)
            {
                if (part is TextPart textPart && !string.IsNullOrEmpty(textPart.Text))
                {
                    return textPart.Text;
                }
            }
        }
        return string.Empty;
    }

    /// <summary>
    /// Summarizes the provided text using AI
    /// </summary>
    private async Task<Message> SummarizeTextAsync(string text)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                var errorMessage = new Message
                {
                    Role = MessageRole.Agent,
                    MessageId = Guid.NewGuid().ToString(),
                    ContextId = contextId,
                    Parts = [new TextPart { Text = "Error: No text provided for summarization" }]
                };
                return errorMessage;
            }

            _logger.LogInformation("Summarizing text of length: {Length}", text.Length);

            var prompt = $@"
Summarize the following text in 2-3 sentences:

{text}

Summary:";

            var result = await _kernel.InvokePromptAsync(prompt);
            var summary = result.GetValue<string>() ?? "Unable to generate summary";

            var response = new
            {
                OriginalLength = text.Length,
                Summary = summary.Trim(),
                CompressionRatio = Math.Round((double)summary.Length / text.Length * 100, 1),
                Function = "Text Summarization"
            };

            var responseText = JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });

            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = responseText }]
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error summarizing text");
            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = $"Error: Summarization failed: {ex.Message}" }]
            };
        }
    }

    /// <summary>
    /// Analyzes the sentiment of the provided text
    /// </summary>
    private async Task<Message> AnalyzeSentimentAsync(string text)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return new Message
                {
                    Role = MessageRole.Agent,
                    MessageId = Guid.NewGuid().ToString(),
                    ContextId = "",
                    Parts = [new TextPart { Text = "Error: No text provided for sentiment analysis" }]
                };
            }

            _logger.LogInformation("Analyzing sentiment for text of length: {Length}", text.Length);

            var prompt = $@"
Analyze the sentiment of the following text and provide:
1. Overall sentiment (Positive, Negative, or Neutral)
2. Confidence score (0-100)
3. Key emotional indicators found in the text

Text: {text}

Respond in this format:
Sentiment: [Positive/Negative/Neutral]
Confidence: [0-100]
Emotions: [emotion1, emotion2, ...]
Explanation: [Brief explanation]";

            var result = await _kernel.InvokePromptAsync(prompt);
            var analysis = result.GetValue<string>() ?? "Analysis unavailable";

            var response = new
            {
                OriginalText = text,
                Analysis = analysis,
                Function = "Sentiment Analysis"
            };

            var responseText = JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });

            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = responseText }]
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing sentiment");
            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = $"Error: Sentiment analysis failed: {ex.Message}" }]
            };
        }
    }

    /// <summary>
    /// Generates creative ideas based on a topic or prompt
    /// </summary>
    private async Task<Message> GenerateIdeasAsync(string topic)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(topic))
            {
                return new Message
                {
                    Role = MessageRole.Agent,
                    MessageId = Guid.NewGuid().ToString(),
                    ContextId = "",
                    Parts = [new TextPart { Text = "Error: No topic provided for idea generation" }]
                };
            }

            _logger.LogInformation("Generating ideas for topic: {Topic}", topic);

            var prompt = $@"
Generate 5 creative and practical ideas related to: {topic}

Format each idea as:
- **Idea Name**: Brief description

Ideas:";

            var result = await _kernel.InvokePromptAsync(prompt);
            var ideas = result.GetValue<string>() ?? "No ideas generated";

            var response = new
            {
                Topic = topic,
                Ideas = ideas.Trim(),
                Function = "Idea Generation"
            };

            var responseText = JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });

            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = responseText }]
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating ideas");
            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = $"Error: Idea generation failed: {ex.Message}" }]
            };
        }
    }

    /// <summary>
    /// Translates text between languages
    /// </summary>
    private async Task<Message> TranslateTextAsync(string text, string targetLanguage = "Spanish")
    {
        try
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return new Message
                {
                    Role = MessageRole.Agent,
                    MessageId = Guid.NewGuid().ToString(),
                    ContextId = "",
                    Parts = [new TextPart { Text = "Error: No text provided for translation" }]
                };
            }

            _logger.LogInformation("Translating text to: {Language}", targetLanguage);

            var prompt = $@"
Translate the following text to {targetLanguage}:

{text}

Translation:";

            var result = await _kernel.InvokePromptAsync(prompt);
            var translation = result.GetValue<string>() ?? "Translation unavailable";

            var response = new
            {
                OriginalText = text,
                TranslatedText = translation.Trim(),
                TargetLanguage = targetLanguage,
                Function = "Text Translation"
            };

            var responseText = JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });

            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = responseText }]
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error translating text");
            return new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = "",
                Parts = [new TextPart { Text = $"Error: Translation failed: {ex.Message}" }]
            };
        }
    }

    /// <summary>
    /// Returns the capabilities of this AI agent
    /// </summary>
    private Task<Message> GetCapabilitiesAsync()
    {
        var capabilities = new
        {
            Agent = "AI Agent powered by Semantic Kernel",
            Functions = new[]
            {
                "📝 summarize:[text] - Summarizes long text into key points",
                "😊 sentiment:[text] - Analyzes emotional sentiment of text",
                "💡 ideas:[topic] - Generates creative ideas for any topic",
                "🌍 translate:[text] - Translates text to Spanish",
                "❓ help - Shows this help information"
            },
            Examples = new[]
            {
                "summarize: Artificial intelligence is revolutionizing the way we work...",
                "sentiment: I love this new technology! It's amazing and so helpful.",
                "ideas: sustainable software development",
                "translate: Hello, how are you today?",
                "help"
            },
            PoweredBy = "Microsoft Semantic Kernel",
            Version = "1.0.0"
        };

        var responseText = JsonSerializer.Serialize(capabilities, new JsonSerializerOptions { WriteIndented = true });

        return Task.FromResult(new Message
        {
            Role = MessageRole.Agent,
            MessageId = Guid.NewGuid().ToString(),
            ContextId = "",
            Parts = [new TextPart { Text = responseText }]
        });
    }

    /// <summary>
    /// Returns agent information for discovery
    /// </summary>
    private Task<AgentCard> GetAgentCardAsync(string agentUrl, CancellationToken cancellationToken)
    {
        var agentCard = new AgentCard
        {
            Name = "AI Agent",
            Description = "AI-powered agent using Semantic Kernel for text processing and analysis",
            Url = agentUrl,
            Version = "1.0.0",
            DefaultInputModes = ["text"],
            DefaultOutputModes = ["text"],
            Capabilities = new AgentCapabilities { Streaming = false }
        };

        return Task.FromResult(agentCard);
    }
}
