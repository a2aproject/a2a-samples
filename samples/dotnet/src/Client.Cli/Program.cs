using System.CommandLine;
using GitHubAgentCli.Commands;
using GitHubAgentCli.Configuration;
using GitHubAgentCli.Handlers;
using GitHubAgentCli.Utilities;

namespace GitHubAgentCli;

public static class Program
{
    public static Task<int> Main(string[] args)
    {
        NetworkUtilities.DisableSslCertificateValidation();

        RootCommand rootCommand = new("GitHub Agent CLI - Enhanced A2A Client for GitHub Agent")
        {
            CliConfiguration.AgentOption,
            CliConfiguration.SessionOption,
            CliConfiguration.HistoryOption,
            CliConfiguration.UsePushNotificationsOption,
            CliConfiguration.PushNotificationReceiverOption,
            CliConfiguration.ModeOption
        };

        Command a2aCommand = CommandFactory.CreateA2ACommand();
        Command apiCommand = CommandFactory.CreateApiCommand();
        Command statusCommand = CommandFactory.CreateStatusCommand();
        Command toolsCommand = CommandFactory.CreateToolsCommand();
        Command interactiveCommand = CommandFactory.CreateInteractiveCommand();

        rootCommand.Add(a2aCommand);
        rootCommand.Add(apiCommand);
        rootCommand.Add(statusCommand);
        rootCommand.Add(toolsCommand);
        rootCommand.Add(interactiveCommand);

        rootCommand.SetHandler(
            CommandHandlers.RunA2ACliAsync,
            CliConfiguration.AgentOption,
            CliConfiguration.SessionOption,
            CliConfiguration.HistoryOption,
            CliConfiguration.UsePushNotificationsOption,
            CliConfiguration.PushNotificationReceiverOption);

        return rootCommand.InvokeAsync(args);
    }
}