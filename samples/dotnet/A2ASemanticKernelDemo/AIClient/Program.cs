using A2A;

namespace AIClient;

class Program
{
    private const string AI_AGENT_URL = "http://localhost:5000";

    static async Task Main(string[] args)
    {
        Console.WriteLine("🤖 A2A Semantic Kernel AI Client");
        Console.WriteLine("==================================");
        Console.WriteLine();

        try
        {
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
    }

    static async Task TestConnection()
    {
        var client = new A2AClient(new Uri(AI_AGENT_URL));

        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = "help" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });
        if (response is not Message)
        {
            throw new Exception("Failed to connect to AI Agent");
        }

        Console.WriteLine($"📡 Connected to AI Agent at {AI_AGENT_URL}...");
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

        var client = new A2AClient(new Uri(AI_AGENT_URL));
        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"summarize: {text}" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });

        if (response is Message responseMessage && responseMessage.Parts.Count > 0)
        {
            var textPart = responseMessage.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart != null)
            {
                Console.WriteLine("\n✅ Summary Result:");
                Console.WriteLine(textPart.Text);
            }
        }
        else
        {
            Console.WriteLine("❌ Summarization failed.");
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

        var client = new A2AClient(new Uri(AI_AGENT_URL));
        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"sentiment: {text}" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });

        if (response is Message responseMessage && responseMessage.Parts.Count > 0)
        {
            var textPart = responseMessage.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart != null)
            {
                Console.WriteLine("\n✅ Sentiment Analysis Result:");
                Console.WriteLine(textPart.Text);
            }
        }
        else
        {
            Console.WriteLine("❌ Sentiment analysis failed.");
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

        var client = new A2AClient(new Uri(AI_AGENT_URL));
        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"ideas: {topic}" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });

        if (response is Message responseMessage && responseMessage.Parts.Count > 0)
        {
            var textPart = responseMessage.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart != null)
            {
                Console.WriteLine("\n✅ Generated Ideas:");
                Console.WriteLine(textPart.Text);
            }
        }
        else
        {
            Console.WriteLine("❌ Idea generation failed.");
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

        var client = new A2AClient(new Uri(AI_AGENT_URL));
        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"translate: {text}" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });

        if (response is Message responseMessage && responseMessage.Parts.Count > 0)
        {
            var textPart = responseMessage.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart != null)
            {
                Console.WriteLine("\n✅ Translation Result:");
                Console.WriteLine(textPart.Text);
            }
        }
        else
        {
            Console.WriteLine("❌ Translation failed.");
        }
    }

    static async Task RunDemoScenarios()
    {
        Console.WriteLine("\n🎬 Running Demo Scenarios...");
        Console.WriteLine("=====================================");

        var client = new A2AClient(new Uri(AI_AGENT_URL));

        // Demo 1: Text Summarization
        Console.WriteLine("\n1️⃣  Text Summarization Demo");
        var demoText = "Artificial Intelligence has rapidly evolved over the past decade, transforming industries and reshaping how we work and live. Machine learning algorithms can now process vast amounts of data, recognize patterns, and make predictions with unprecedented accuracy.";

        var message1 = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"summarize: {demoText}" }]
        };
        var response1 = await client.SendMessageAsync(new MessageSendParams { Message = message1 });
        if (response1 is Message responseMessage1 && responseMessage1.Parts.Count > 0)
        {
            var textPart1 = responseMessage1.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart1 != null)
            {
                Console.WriteLine("✅ Summary Result:");
                Console.WriteLine(textPart1.Text);
            }
        }

        // Demo 2: Sentiment Analysis
        Console.WriteLine("\n2️⃣  Sentiment Analysis Demo");
        var sentimentText = "I absolutely love working with this new technology! It's incredibly powerful and makes our development process so much more efficient. The team is excited about the possibilities.";

        var message2 = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = $"sentiment: {sentimentText}" }]
        };
        var response2 = await client.SendMessageAsync(new MessageSendParams { Message = message2 });
        if (response2 is Message responseMessage2 && responseMessage2.Parts.Count > 0)
        {
            var textPart2 = responseMessage2.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart2 != null)
            {
                Console.WriteLine("✅ Sentiment Result:");
                Console.WriteLine(textPart2.Text);
            }
        }

        // Demo 3: Idea Generation
        Console.WriteLine("\n3️⃣  Idea Generation Demo");
        var message3 = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = "ideas: sustainable software development" }]
        };
        var response3 = await client.SendMessageAsync(new MessageSendParams { Message = message3 });
        if (response3 is Message responseMessage3 && responseMessage3.Parts.Count > 0)
        {
            var textPart3 = responseMessage3.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart3 != null)
            {
                Console.WriteLine("✅ Ideas Result:");
                Console.WriteLine(textPart3.Text);
            }
        }

        Console.WriteLine("\n✅ Demo completed!");
    }

    static async Task ShowCapabilities()
    {
        Console.WriteLine("\n🔍 AI Agent Capabilities");

        var client = new A2AClient(new Uri(AI_AGENT_URL));
        var message = new Message
        {
            Role = MessageRole.User,
            MessageId = Guid.NewGuid().ToString(),
            Parts = [new TextPart { Text = "help" }]
        };

        var response = await client.SendMessageAsync(new MessageSendParams { Message = message });

        if (response is Message responseMessage && responseMessage.Parts.Count > 0)
        {
            var textPart = responseMessage.Parts.OfType<TextPart>().FirstOrDefault();
            if (textPart != null)
            {
                Console.WriteLine("✅ Available functions:");
                Console.WriteLine(textPart.Text);
            }
        }
        else
        {
            Console.WriteLine("❌ Failed to get capabilities.");
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
