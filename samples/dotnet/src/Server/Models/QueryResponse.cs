namespace Server.Models;

public class QueryResponse
{
    public string Query { get; set; } = string.Empty;
    public string Response { get; set; } = string.Empty;
    public DateTime ProcessedAt { get; set; }
    public string? ContextId { get; set; }
}