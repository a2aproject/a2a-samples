using A2A;
using GitHubAgentCli.Configuration;
using GitHubAgentCli.Utilities;
using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace GitHubAgentCli.Services;

public class A2AService(ILogger logger)
{
    private readonly ILogger _logger = logger;

    public async Task<bool> CompleteTaskAsync(
        A2AClient client,
        bool streaming,
        bool usePushNotifications,
        string notificationReceiverHost,
        int notificationReceiverPort,
        string taskId,
        string sessionId,
        CancellationToken cancellationToken)
    {
        Console.Write("github-agent> ");
        string? prompt = Console.ReadLine();

        if (string.IsNullOrWhiteSpace(prompt))
        {
            Console.WriteLine("Request cannot be empty.");
            return true;
        }

        if (prompt is ":q" or "quit")
        {
            return false;
        }

        Message message = new()
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            ContextId = sessionId,
            Parts = [new TextPart { Text = prompt }]
        };


        MessageSendParams payload = new()
        {
            Configuration = new()
            {
                AcceptedOutputModes = ["text"]
            },
            Message = message
        };

        if (usePushNotifications)
        {
            payload.Configuration.PushNotification = new PushNotificationConfig
            {
                Url = $"http://{notificationReceiverHost}:{notificationReceiverPort}/notify",
                Authentication = new PushNotificationAuthenticationInfo
                {
                    Schemes = ["bearer"]
                }
            };
        }

        try
        {
            Console.WriteLine("\nProcessing your request...");

            A2AResponse response = await client.SendMessageAsync(payload, cancellationToken);

            Console.WriteLine("\nResponse:");
            Console.WriteLine("─────────");

            if (response is Message responseMessage)
            {
                IEnumerable<TextPart> textParts = responseMessage.Parts.OfType<TextPart>();
                foreach (TextPart textPart in textParts)
                {
                    Console.WriteLine(textPart.Text);
                }
            }
            else if (response is AgentTask agentTask)
            {
                agentTask.Artifacts?
                    .SelectMany(artifact => artifact.Parts.OfType<TextPart>())
                    .ToList()
                    .ForEach(textPart => Console.WriteLine(textPart.Text));
            }
            else
            {
                Console.WriteLine(JsonSerializer.Serialize(response, CliConfiguration.IndentOptions));
            }

            Console.WriteLine();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }

        return true;
    }
}