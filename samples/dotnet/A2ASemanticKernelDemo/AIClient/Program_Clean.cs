using A2A;

namespace AIClient;

class Program
{
    private static A2AClient? _client;
    private const string AI_AGENT_URL = "http://localhost:5000";

    static async Task Main(string[] args)
    {
        Console.WriteLine("🤖 A2A Semantic Kernel AI Client");
        Console.WriteLine("==================================");
        Console.WriteLine();

        try
        {
            // Initialize A2A client
            _client = new A2AClient();

            Console.WriteLine($"📡 Connecting to AI Agent at {AI_AGENT_URL}...");

            // Test connection by getting capabilities
            await TestConnection();

            Console.WriteLine("✅ Connected successfully!");
            Console.WriteLine();

            // Show help menu
            await ShowHelp();

            // Main interaction loop
            await InteractionLoop();
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
            Console.WriteLine();
            Console.WriteLine("🔧 Troubleshooting:");
            Console.WriteLine("   1. Make sure the AI Server is running");
            Console.WriteLine("   2. Check if port 5000 is available");
            Console.WriteLine("   3. Verify the server URL is correct");
        }
        finally
        {
            _client?.Dispose();
        }
    }

    static async Task TestConnection()
    {
        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), "help");
        if (!response.IsSuccess)
        {
            throw new Exception($"Failed to connect to AI Agent: {response.ErrorMessage}");
        }
    }

    static async Task InteractionLoop()
    {
        while (true)
        {
            Console.Write("\n🎯 Choose an option (1-6, 'help', or 'quit'): ");
            var input = Console.ReadLine()?.Trim().ToLower();

            try
            {
                switch (input)
                {
                    case "1" or "summarize":
                        await HandleSummarize();
                        break;
                    case "2" or "sentiment":
                        await HandleSentiment();
                        break;
                    case "3" or "ideas":
                        await HandleIdeas();
                        break;
                    case "4" or "translate":
                        await HandleTranslate();
                        break;
                    case "5" or "demo":
                        await RunDemoScenarios();
                        break;
                    case "6" or "capabilities":
                        await ShowCapabilities();
                        break;
                    case "help" or "h" or "?":
                        await ShowHelp();
                        break;
                    case "quit" or "exit" or "q":
                        Console.WriteLine("👋 Goodbye!");
                        return;
                    case "":
                        continue;
                    default:
                        Console.WriteLine("❓ Unknown option. Type 'help' for available commands.");
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Error: {ex.Message}");
            }
        }
    }

    static async Task HandleSummarize()
    {
        Console.WriteLine("\n📝 Text Summarization");
        Console.WriteLine("Enter the text you want to summarize (press Enter twice to finish):");

        var text = ReadMultilineInput();
        if (string.IsNullOrWhiteSpace(text))
        {
            Console.WriteLine("❌ No text provided.");
            return;
        }

        Console.WriteLine("\n🔄 Summarizing...");

        var message = $"summarize: {text}";
        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), message);

        if (response.IsSuccess)
        {
            Console.WriteLine("\n✅ Summary Result:");
            Console.WriteLine(response.TextData);
        }
        else
        {
            Console.WriteLine($"❌ Summarization failed: {response.ErrorMessage}");
        }
    }

    static async Task HandleSentiment()
    {
        Console.WriteLine("\n😊 Sentiment Analysis");
        Console.WriteLine("Enter the text to analyze:");

        var text = ReadMultilineInput();
        if (string.IsNullOrWhiteSpace(text))
        {
            Console.WriteLine("❌ No text provided.");
            return;
        }

        Console.WriteLine("\n🔄 Analyzing sentiment...");

        var message = $"sentiment: {text}";
        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), message);

        if (response.IsSuccess)
        {
            Console.WriteLine("\n✅ Sentiment Analysis Result:");
            Console.WriteLine(response.TextData);
        }
        else
        {
            Console.WriteLine($"❌ Sentiment analysis failed: {response.ErrorMessage}");
        }
    }

    static async Task HandleIdeas()
    {
        Console.WriteLine("\n💡 Idea Generation");
        Console.Write("Enter a topic or challenge: ");
        var topic = Console.ReadLine();

        if (string.IsNullOrWhiteSpace(topic))
        {
            Console.WriteLine("❌ No topic provided.");
            return;
        }

        Console.WriteLine("\n🔄 Generating ideas...");

        var message = $"ideas: {topic}";
        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), message);

        if (response.IsSuccess)
        {
            Console.WriteLine("\n✅ Generated Ideas:");
            Console.WriteLine(response.TextData);
        }
        else
        {
            Console.WriteLine($"❌ Idea generation failed: {response.ErrorMessage}");
        }
    }

    static async Task HandleTranslate()
    {
        Console.WriteLine("\n🌍 Text Translation");
        Console.WriteLine("Enter the text to translate:");

        var text = ReadMultilineInput();
        if (string.IsNullOrWhiteSpace(text))
        {
            Console.WriteLine("❌ No text provided.");
            return;
        }

        Console.WriteLine("\n🔄 Translating to Spanish...");

        var message = $"translate: {text}";
        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), message);

        if (response.IsSuccess)
        {
            Console.WriteLine("\n✅ Translation Result:");
            Console.WriteLine(response.TextData);
        }
        else
        {
            Console.WriteLine($"❌ Translation failed: {response.ErrorMessage}");
        }
    }

    static async Task RunDemoScenarios()
    {
        Console.WriteLine("\n🎬 Running Demo Scenarios...");
        Console.WriteLine("=====================================");

        // Demo 1: Text Summarization
        Console.WriteLine("\n1️⃣  Text Summarization Demo");
        var demoText = "Artificial Intelligence has rapidly evolved over the past decade, transforming industries and reshaping how we work and live. Machine learning algorithms can now process vast amounts of data, recognize patterns, and make predictions with unprecedented accuracy.";

        var response1 = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), $"summarize: {demoText}");
        if (response1.IsSuccess)
        {
            Console.WriteLine("✅ Summary Result:");
            Console.WriteLine(response1.TextData);
        }

        // Demo 2: Sentiment Analysis
        Console.WriteLine("\n2️⃣  Sentiment Analysis Demo");
        var sentimentText = "I absolutely love working with this new technology! It's incredibly powerful and makes our development process so much more efficient. The team is excited about the possibilities.";

        var response2 = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), $"sentiment: {sentimentText}");
        if (response2.IsSuccess)
        {
            Console.WriteLine("✅ Sentiment Result:");
            Console.WriteLine(response2.TextData);
        }

        // Demo 3: Idea Generation
        Console.WriteLine("\n3️⃣  Idea Generation Demo");
        var response3 = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), "ideas: sustainable software development");
        if (response3.IsSuccess)
        {
            Console.WriteLine("✅ Ideas Result:");
            Console.WriteLine(response3.TextData);
        }

        Console.WriteLine("\n✅ Demo completed!");
    }

    static async Task ShowCapabilities()
    {
        Console.WriteLine("\n🔍 AI Agent Capabilities");

        var response = await _client!.SendTextAsync(new Uri(AI_AGENT_URL), "help");

        if (response.IsSuccess)
        {
            Console.WriteLine("✅ Available functions:");
            Console.WriteLine(response.TextData);
        }
        else
        {
            Console.WriteLine($"❌ Failed to get capabilities: {response.ErrorMessage}");
        }
    }

    static Task ShowHelp()
    {
        Console.WriteLine("🎯 Available Options:");
        Console.WriteLine();
        Console.WriteLine("   1. 📝 Summarize Text    - Condense long text into key points");
        Console.WriteLine("   2. 😊 Sentiment Analysis - Analyze emotional tone of text");
        Console.WriteLine("   3. 💡 Generate Ideas     - Create brainstorming suggestions");
        Console.WriteLine("   4. 🌍 Translate Text     - Convert text to Spanish");
        Console.WriteLine("   5. 🎬 Run Demo          - See all features in action");
        Console.WriteLine("   6. 🔍 Show Capabilities - List all AI agent functions");
        Console.WriteLine();
        Console.WriteLine("Commands: help, quit");
        Console.WriteLine();

        return Task.CompletedTask;
    }

    static string ReadMultilineInput()
    {
        var lines = new List<string>();
        string? line;

        while ((line = Console.ReadLine()) != null)
        {
            if (string.IsNullOrEmpty(line))
                break;
            lines.Add(line);
        }

        return string.Join(" ", lines);
    }
}
