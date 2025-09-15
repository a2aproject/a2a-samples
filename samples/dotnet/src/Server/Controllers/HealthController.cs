using Microsoft.AspNetCore.Mvc;
using ModelContextProtocol.Client;
using Server.Services;

namespace Server.Controllers;

[ApiController]
[Route("api/[controller]")]
public class HealthController(GitHubA2AAgent githubAgent, ILogger<HealthController> logger) : ControllerBase
{
    /// <summary>
    /// Basic health check
    /// </summary>
    [HttpGet]
    public IActionResult Get()
    {
        return Ok(new
        {
            Status = "Healthy",
            Timestamp = DateTime.UtcNow,
            Service = "GitHub A2A Agent Server"
        });
    }

    /// <summary>
    /// Detailed health check including dependencies
    /// </summary>
    [HttpGet("detailed")]
    public async Task<IActionResult> GetDetailed()
    {
        try
        {
            var health = new
            {
                Status = "Healthy",
                Timestamp = DateTime.UtcNow,
                Service = "GitHub A2A Agent Server",
                Components = new
                {
                    Agent = new
                    {
                        Status = githubAgent.IsInitialized ? "Healthy" : "Initializing",
                        InitializedAt = githubAgent.InitializedAt
                    },
                    McpClient = await CheckMcpClientHealthAsync(),
                    Environment = new
                    {
                        OpenAIConfigured = !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("OPENAI_API_KEY")),
                        ModelName = Environment.GetEnvironmentVariable("OPENAI_MODEL_NAME") ?? "gpt-4o-mini"
                    }
                }
            };

            return Ok(health);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error performing detailed health check");
            return StatusCode(500, new
            {
                Status = "Unhealthy",
                Timestamp = DateTime.UtcNow,
                Error = ex.Message
            });
        }
    }

    private async Task<object> CheckMcpClientHealthAsync()
    {
        try
        {
            if (!githubAgent.IsInitialized)
            {
                return new { Status = "Not Initialized" };
            }

            IList<McpClientTool> tools = await githubAgent.GetAvailableToolsAsync();
            return new
            {
                Status = "Healthy",
                ToolsCount = tools.Count,
                LastChecked = DateTime.UtcNow
            };
        }
        catch (Exception ex)
        {
            return new
            {
                Status = "Unhealthy",
                Error = ex.Message,
                LastChecked = DateTime.UtcNow
            };
        }
    }
}