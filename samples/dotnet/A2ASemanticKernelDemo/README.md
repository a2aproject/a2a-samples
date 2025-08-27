# A2A Semantic Kernel AI Demo

This demo showcases how to build **AI-powered agents** using the A2A framework with Microsoft Semantic Kernel. The demo includes intelligent text processing capabilities like summarization, sentiment analysis, idea generation, and translation.

## 🎯 What You'll Learn

- **AI Agent Integration**: How to combine A2A with Semantic Kernel
- **Intelligent Functions**: Building agents that understand and process natural language
- **AI Service Configuration**: Setting up different AI providers (Azure OpenAI, OpenAI, etc.)
- **Advanced Scenarios**: Real-world AI agent use cases

## 🚀 Quick Start

### Option 1: One-Click Demo
```bash
run_demo.bat
```

### Option 2: Manual Setup

**Terminal 1 - AI Server:**
```bash
cd AIServer
dotnet run --urls=http://localhost:5000
```

**Terminal 2 - AI Client:**
```bash
cd AIClient
dotnet run
```

## 🤖 Available AI Functions

### 📝 Text Summarization
- **Function**: `summarize_text`
- **Purpose**: Condenses long text into key points
- **Example**: Summarize articles, reports, or documentation

### 😊 Sentiment Analysis  
- **Function**: `analyze_sentiment`
- **Purpose**: Analyzes emotional tone and sentiment
- **Example**: Evaluate customer feedback or social media content

### 💡 Idea Generation
- **Function**: `generate_ideas`
- **Purpose**: Generates creative suggestions for any topic
- **Example**: Brainstorming, problem-solving, innovation

### 🌍 Text Translation
- **Function**: `translate_text`
- **Purpose**: Translates between different languages
- **Example**: Multilingual communication and content localization

### 🔍 Capabilities Discovery
- **Function**: `get_capabilities`
- **Purpose**: Lists all available AI functions
- **Example**: Dynamic discovery of agent capabilities

## 🛠️ Configuration

### AI Service Setup

The demo includes a **mock AI service** for immediate testing. For production use, configure a real AI provider.

### Environment Variables
```bash
# For Azure OpenAI
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment

# For OpenAI
OPENAI_API_KEY=your-key
```

## 🎬 Demo Scenarios

### 1. Document Summarization
```
Input: Long research paper or article
Output: Concise 2-3 sentence summary with key insights
```

### 2. Customer Feedback Analysis
```
Input: Customer reviews or feedback
Output: Sentiment classification with confidence scores
```

### 3. Creative Brainstorming
```
Input: Business challenge or topic
Output: Multiple creative solutions and approaches
```

### 4. Multilingual Content
```
Input: Text in any language
Output: Professional translation to target language
```

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/A2A     ┌─────────────────┐
│   AI Client     │ ──────────────► │   AI Server     │
│                 │                 │                 │
│ • Interactive   │                 │ • AIAgent       │
│ • Demonstrations│                 │ • Semantic      │
│ • Examples      │                 │   Kernel        │
└─────────────────┘                 │ • AI Functions  │
                                    └─────────────────┘
                                            │
                                            ▼
                                    ┌─────────────────┐
                                    │  AI Provider    │
                                    │                 │
                                    │ • Azure OpenAI  │
                                    │ • OpenAI        │
                                    │ • Other Models  │
                                    └─────────────────┘
```

## 🔧 Customization

### Adding New AI Functions
1. **Define the function** in `AIAgent.cs`
2. **Register it** in the `Attach()` method
3. **Add request/response models**
4. **Update the client** with new options

### Example: Adding Text Classification
```csharp
[Description("Classifies text into categories")]
public async Task<Message> ClassifyTextAsync(MessageSendParams parameters)
{
    var request = JsonSerializer.Deserialize<ClassifyRequest>(parameters.Data);
    
    var prompt = $"Classify this text into categories: {request.Text}";
    var result = await _kernel.InvokePromptAsync(prompt);
    
    return Message.Success(new ClassifyResponse(result.GetValue<string>()));
}
```

## 📊 Advanced Features

### Streaming Responses
- Real-time AI output for long responses
- Enhanced user experience
- Progressive result display

### Context Management
- Multi-turn conversations
- Context-aware responses
- Conversation history

### Plugin Integration
- Semantic Kernel plugins
- External API integration
- Custom function calling

### Debug Mode
Add this to see detailed AI interactions:
```csharp
builder.Logging.SetMinimumLevel(LogLevel.Debug);
```

## 🎓 Learning Resources

- **[Semantic Kernel Documentation](https://learn.microsoft.com/en-us/semantic-kernel/)**
- **[A2A Framework Guide](../README.md)**
- **[Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)**
