using System.Net;

namespace GitHubAgentCli.Utilities;

public static class NetworkUtilities
{
    public static void DisableSslCertificateValidation()
    {
        // SSL Certificate validation disabled for development
        ServicePointManager.ServerCertificateValidationCallback =
            (_, _, _, _) => true;
    }

    public static void ConfigureSslCertificateValidation()
    {
    }

    public static HttpClient CreateHttpClient()
    {
        HttpClientHandler handler = new();
        handler.ServerCertificateCustomValidationCallback = (_, _, _, _) => true;
        return new HttpClient(handler);
    }

    public static string NormalizeUrl(string url)
    {
        url = url.TrimEnd('/');

        if (url.StartsWith("http://") || url.StartsWith("https://"))
        {
            return url;
        }

        if (url.Contains("localhost") || url.Contains("127.0.0.1"))
        {
            url = "http://" + url;
        }
        else
        {
            url = "https://" + url;
        }

        return url;
    }
}