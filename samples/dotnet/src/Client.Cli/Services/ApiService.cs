using GitHubAgentCli.Configuration;
using GitHubAgentCli.Utilities;
using System.Net.Http.Json;
using System.Text.Json;

namespace GitHubAgentCli.Services;

public static class ApiService
{
    public static async Task RunQueryAsync(string baseUrl, string query)
    {
        try
        {
            NetworkUtilities.ConfigureSslCertificateValidation();

            Console.WriteLine("GitHub Agent API Query");
            Console.WriteLine("═════════════════════");
            Console.WriteLine($"Server: {baseUrl}");
            Console.WriteLine($"Query: {query}");
            Console.WriteLine();

            string normalizedUrl = NetworkUtilities.NormalizeUrl(baseUrl);

            using HttpClient httpClient = NetworkUtilities.CreateHttpClient();
            var request = new { Query = query };

            HttpResponseMessage response = await httpClient.PostAsJsonAsync($"{normalizedUrl}/api/githubagent/query", request);

            if (response.IsSuccessStatusCode)
            {
                string result = await response.Content.ReadAsStringAsync();
                JsonDocument jsonDoc = JsonDocument.Parse(result);

                Console.WriteLine("Response:");
                Console.WriteLine("─────────");

                if (jsonDoc.RootElement.TryGetProperty("response", out JsonElement responseProperty))
                {
                    Console.WriteLine(responseProperty.GetString());
                }
                else
                {
                    Console.WriteLine(JsonSerializer.Serialize(jsonDoc, CliConfiguration.IndentOptions));
                }
            }
            else
            {
                Console.WriteLine($"Error: {response.StatusCode}");
                string error = await response.Content.ReadAsStringAsync();
                Console.WriteLine(error);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }

    public static async Task GetStatusAsync(string baseUrl)
    {
        try
        {
            NetworkUtilities.ConfigureSslCertificateValidation();

            Console.WriteLine("GitHub Agent Status");
            Console.WriteLine("══════════════════");

            string normalizedUrl = NetworkUtilities.NormalizeUrl(baseUrl);

            using HttpClient httpClient = NetworkUtilities.CreateHttpClient();
            HttpResponseMessage response = await httpClient.GetAsync($"{normalizedUrl}/api/githubagent/status");

            if (response.IsSuccessStatusCode)
            {
                string result = await response.Content.ReadAsStringAsync();
                JsonDocument jsonDoc = JsonDocument.Parse(result);
                Console.WriteLine(JsonSerializer.Serialize(jsonDoc, CliConfiguration.IndentOptions));
            }
            else
            {
                Console.WriteLine($"Error: {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }

    public static async Task GetAvailableToolsAsync(string baseUrl)
    {
        try
        {
            NetworkUtilities.ConfigureSslCertificateValidation();

            Console.WriteLine("Available GitHub Tools");
            Console.WriteLine("════════════════════");

            string normalizedUrl = NetworkUtilities.NormalizeUrl(baseUrl);

            using HttpClient httpClient = NetworkUtilities.CreateHttpClient();
            HttpResponseMessage response = await httpClient.GetAsync($"{normalizedUrl}/api/githubagent/tools");

            if (response.IsSuccessStatusCode)
            {
                string result = await response.Content.ReadAsStringAsync();
                JsonDocument jsonDoc = JsonDocument.Parse(result);
                Console.WriteLine(JsonSerializer.Serialize(jsonDoc, CliConfiguration.IndentOptions));
            }
            else
            {
                Console.WriteLine($"Error: {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }
}