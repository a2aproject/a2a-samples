using System.CommandLine;
using GitHubAgentCli.Configuration;
using GitHubAgentCli.Handlers;

namespace GitHubAgentCli.Commands;

public static class CommandFactory
{
    public static Command CreateA2ACommand()
    {
        Command command = new("a2a", "Use A2A protocol to communicate with the agent")
        {
            CliConfiguration.AgentOption,
            CliConfiguration.SessionOption,
            CliConfiguration.HistoryOption,
            CliConfiguration.UsePushNotificationsOption,
            CliConfiguration.PushNotificationReceiverOption
        };
        command.SetHandler(
            CommandHandlers.RunA2ACliAsync,
            CliConfiguration.AgentOption,
            CliConfiguration.SessionOption,
            CliConfiguration.HistoryOption,
            CliConfiguration.UsePushNotificationsOption,
            CliConfiguration.PushNotificationReceiverOption);
        return command;
    }

    public static Command CreateApiCommand()
    {
        Argument<string> queryArgument = new("query", "The query to send to the GitHub agent");
        Command command = new("api", "Use direct API to communicate with the agent")
        {
            CliConfiguration.AgentOption,
            queryArgument
        };
        command.SetHandler(CommandHandlers.RunApiQueryAsync, CliConfiguration.AgentOption, queryArgument);
        return command;
    }

    public static Command CreateStatusCommand()
    {
        Command command = new("status", "Get agent status and information")
        {
            CliConfiguration.AgentOption
        };
        command.SetHandler(CommandHandlers.GetAgentStatusAsync, CliConfiguration.AgentOption);
        return command;
    }

    public static Command CreateToolsCommand()
    {
        Command command = new("tools", "List available GitHub tools")
        {
            CliConfiguration.AgentOption
        };
        command.SetHandler(CommandHandlers.GetAvailableToolsAsync, CliConfiguration.AgentOption);
        return command;
    }

    public static Command CreateInteractiveCommand()
    {
        Command command = new("interactive", "Start interactive session")
        {
            CliConfiguration.AgentOption,
            CliConfiguration.ModeOption
        };
        command.SetHandler(CommandHandlers.RunInteractiveSessionAsync, CliConfiguration.AgentOption, CliConfiguration.ModeOption);
        return command;
    }
}