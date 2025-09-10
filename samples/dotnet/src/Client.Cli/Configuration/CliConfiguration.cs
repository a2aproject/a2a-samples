using System.CommandLine;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace GitHubAgentCli.Configuration;

public static class CliConfiguration
{
    public static readonly Option<string> AgentOption = new("--agent", () => "http://localhost:5000", "Agent base URL");
    public static readonly Option<string> SessionOption = new("--session", () => "0", "Session ID (0 for new session)");
    public static readonly Option<bool> HistoryOption = new("--history", "Show task history");
    public static readonly Option<bool> UsePushNotificationsOption = new("--use-push-notifications", "Enable push notifications");
    public static readonly Option<string> PushNotificationReceiverOption = new("--push-notification-receiver", () => "http://localhost:5000", "Push notification receiver URL");
    public static readonly Option<string> ModeOption = new("--mode", () => "a2a", "Communication mode: 'a2a' or 'api'");

    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
    };

    public static readonly JsonSerializerOptions IndentOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };
}