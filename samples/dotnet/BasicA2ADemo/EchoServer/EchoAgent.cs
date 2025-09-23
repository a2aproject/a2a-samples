using A2A;

namespace EchoServer;

/// <summary>
/// A simple echo agent that responds with the same message it receives.
/// This demonstrates the basic structure of an A2A agent.
/// </summary>
public class EchoAgent
{
    public void Attach(ITaskManager taskManager)
    {
        taskManager.OnMessageReceived = ProcessMessageAsync;
        taskManager.OnAgentCardQuery = GetAgentCardAsync;
    }

    /// <summary>
    /// Handles incoming messages and echoes them back.
    /// </summary>
    private Task<Message> ProcessMessageAsync(MessageSendParams messageSendParams, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<Message>(cancellationToken);
        }

        // Extract the text from the incoming message
        var userText = GetTextFromMessage(messageSendParams.Message);

        Console.WriteLine($"[Echo Agent] Received message: {userText}");

        // Create an echo response
        var responseText = $"Echo: {userText}";

        var responseMessage = new Message
        {
            Role = MessageRole.Agent,
            MessageId = Guid.NewGuid().ToString(),
            ContextId = messageSendParams.Message.ContextId,
            Parts = [new TextPart { Text = responseText }]
        };

        Console.WriteLine($"[Echo Agent] Sending response: {responseText}");

        return Task.FromResult(responseMessage);
    }

    /// <summary>
    /// Retrieves the agent card information for the Echo Agent.
    /// </summary>
    private Task<AgentCard> GetAgentCardAsync(string agentUrl, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<AgentCard>(cancellationToken);
        }

        return Task.FromResult(new AgentCard
        {
            Name = "Simple Echo Agent",
            Description = "A basic agent that echoes back any message you send to it. Perfect for testing A2A communication.",
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
        var textPart = message.Parts.OfType<TextPart>().FirstOrDefault();
        return textPart?.Text ?? "[No text content]";
    }
}
