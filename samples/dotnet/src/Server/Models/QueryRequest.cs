namespace Server.Models;

public class QueryRequest
{
    public string Query { get; set; } = string.Empty;
    public string? ContextId { get; set; }
}