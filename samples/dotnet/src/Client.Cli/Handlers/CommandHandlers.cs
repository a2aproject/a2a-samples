using A2A;
using GitHubAgentCli.Configuration;
using GitHubAgentCli.Services;
using GitHubAgentCli.Utilities;
using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace GitHubAgentCli.Handlers;

public static class CommandHandlers
{
    public static Task RunA2ACliAsync(string agentUrl, string session, bool history, bool usePushNotifications, string pushNotificationReceiver)
    {
        return RunA2ACliAsync(agentUrl, session, history, usePushNotifications, pushNotificationReceiver, CancellationToken.None);
    }

    private static async Task RunA2ACliAsync(
        string agentUrl,
        string session,
        bool history,
        bool usePushNotifications,
        string pushNotificationReceiver,
        CancellationToken cancellationToken)
    {
        NetworkUtilities.ConfigureSslCertificateValidation();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.AddConsole();
            builder.SetMinimumLevel(LogLevel.Information);
        });
        ILogger logger = loggerFactory.CreateLogger("A2AClient");

        try
        {
            Console.WriteLine("GitHub Agent A2A CLI");
            Console.WriteLine("═══════════════════");
            Console.WriteLine($"Connecting to: {agentUrl}");
            Console.WriteLine();

            string normalizedUrl = NetworkUtilities.NormalizeUrl(agentUrl);
            Console.WriteLine($"Normalized URL: {normalizedUrl}");

            A2ACardResolver cardResolver = new(new Uri($"{normalizedUrl}/github-agent"));
            AgentCard card = await cardResolver.GetAgentCardAsync(cancellationToken);

            Console.WriteLine("======= Agent Card ========");
            Console.WriteLine(JsonSerializer.Serialize(card, CliConfiguration.IndentOptions));
            Console.WriteLine();

            Uri notificationReceiverUri = new(pushNotificationReceiver);
            string notificationReceiverHost = notificationReceiverUri.Host;
            int notificationReceiverPort = notificationReceiverUri.Port;

            A2AClient client = new(new Uri(card.Url));
            A2AService a2aService = new(logger);

            string sessionId = session == "0" ? Guid.NewGuid().ToString("N") : session;

            Console.WriteLine($"Session ID: {sessionId}");
            Console.WriteLine("Type 'quit' or ':q' to exit");
            Console.WriteLine();

            bool continueLoop = true;
            bool streaming = card.Capabilities?.Streaming ?? false;

            while (continueLoop)
            {
                string taskId = Guid.NewGuid().ToString("N");

                continueLoop = await a2aService.CompleteTaskAsync(
                    client,
                    streaming,
                    usePushNotifications,
                    notificationReceiverHost,
                    notificationReceiverPort,
                    taskId,
                    sessionId,
                    cancellationToken);

                if (history && continueLoop)
                {
                    Console.WriteLine("\n========= History =========");
                    try
                    {
                        AgentTask taskResponse = await client.GetTaskAsync(taskId, cancellationToken);
                        if (taskResponse.History != null)
                        {
                            taskResponse.History
                                .SelectMany(artifact => artifact.Parts.OfType<TextPart>())
                                .ToList()
                                .ForEach(textPart => Console.WriteLine(textPart.Text));
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Could not retrieve history: {ex.Message}");
                    }
                    Console.WriteLine("===========================\n");
                }
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while running the A2A CLI");
            Console.WriteLine($"Error: {ex.Message}");
        }
    }

    public static async Task RunApiQueryAsync(string baseUrl, string query)
    {
        await ApiService.RunQueryAsync(baseUrl, query);
    }

    public static async Task GetAgentStatusAsync(string baseUrl)
    {
        await ApiService.GetStatusAsync(baseUrl);
    }

    public static async Task GetAvailableToolsAsync(string baseUrl)
    {
        await ApiService.GetAvailableToolsAsync(baseUrl);
    }

    public static async Task RunInteractiveSessionAsync(string baseUrl, string mode)
    {
        await InteractiveService.RunSessionAsync(baseUrl, mode);
    }
}