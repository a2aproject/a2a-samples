using Microsoft.AspNetCore.Mvc;
using ModelContextProtocol.Client;
using Server.Models;
using Server.Services;

namespace Server.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubAgentController(GitHubA2AAgent githubAgent, ILogger<GitHubAgentController> logger) : ControllerBase
{
    /// <summary>
    /// Get agent status and information
    /// </summary>
    [HttpGet("status")]
    public IActionResult GetStatus()
    {
        try
        {
            var status = new
            {
                Name = "GitHub Agent",
                Status = githubAgent.IsInitialized ? "Ready" : "Initializing",
                Version = "1.0.0",
                Capabilities = new[]
                {
                    "Repository Analysis",
                    "Code Search",
                    "Issue Tracking",
                    "Pull Request Analysis",
                    "General GitHub Queries"
                },
                LastInitialized = githubAgent.InitializedAt,
                A2AEndpoint = "/github-agent"
            };

            return Ok(status);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error getting agent status");
            return StatusCode(500, new { error = "Failed to get agent status" });
        }
    }

    /// <summary>
    /// Process a direct query (non-A2A endpoint for testing)
    /// </summary>
    [HttpPost("query")]
    public async Task<IActionResult> ProcessQuery([FromBody] QueryRequest request)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(request.Query))
            {
                return BadRequest(new { error = "Query is required" });
            }

            if (!githubAgent.IsInitialized)
            {
                return ServiceUnavailable(new { error = "Agent is not initialized yet" });
            }

            logger.LogInformation("Processing direct query: {Query}", request.Query);

            string response = await githubAgent.ProcessDirectQueryAsync(request.Query);

            return Ok(new QueryResponse
            {
                Query = request.Query,
                Response = response,
                ProcessedAt = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error processing query: {Query}", request.Query);
            return StatusCode(500, new { error = "Failed to process query", details = ex.Message });
        }
    }

    /// <summary>
    /// Get available GitHub tools
    /// </summary>
    [HttpGet("tools")]
    public async Task<IActionResult> GetTools()
    {
        try
        {
            if (!githubAgent.IsInitialized)
            {
                return ServiceUnavailable(new { error = "Agent is not initialized yet" });
            }

            IList<McpClientTool> tools = await githubAgent.GetAvailableToolsAsync();
            return Ok(new { tools = tools.Select(t => new { t.Name, t.Description }) });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error getting tools");
            return StatusCode(500, new { error = "Failed to get tools" });
        }
    }

    /// <summary>
    /// Reinitialize the agent
    /// </summary>
    [HttpPost("reinitialize")]
    public async Task<IActionResult> Reinitialize()
    {
        try
        {
            logger.LogInformation("Reinitializing GitHub agent");
            await githubAgent.InitializeAsync();
            return Ok(new { message = "Agent reinitialized successfully", timestamp = DateTime.UtcNow });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error reinitializing agent");
            return StatusCode(500, new { error = "Failed to reinitialize agent", details = ex.Message });
        }
    }

    private ObjectResult ServiceUnavailable(object value)
    {
        return StatusCode(503, value);
    }
}