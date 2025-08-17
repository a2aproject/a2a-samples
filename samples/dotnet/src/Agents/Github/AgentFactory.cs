using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace Github;

public class AgentFactory(Kernel kernel)
{
    public ChatCompletionAgent CreateGithubAgent()
    {
        OpenAIPromptExecutionSettings executionSettings = ExecutionSettingsProvider.GetOpenAiSettings();

        return new ChatCompletionAgent
        {
            Instructions = "Answer questions about GitHub repositories.",
            Name = "GitHubAgent",
            Kernel = kernel,
            Arguments = new KernelArguments(executionSettings),
        };
    }
}