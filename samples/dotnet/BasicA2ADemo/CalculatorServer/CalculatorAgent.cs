using A2A;
using System.Text.RegularExpressions;

namespace CalculatorServer;

/// <summary>
/// A simple calculator agent that can perform basic math operations.
/// This demonstrates how to implement business logic in an A2A agent.
/// </summary>
public class CalculatorAgent
{
    public void Attach(ITaskManager taskManager)
    {
        taskManager.OnMessageReceived = ProcessMessageAsync;
        taskManager.OnAgentCardQuery = GetAgentCardAsync;
    }

    /// <summary>
    /// Handles incoming messages and performs calculations.
    /// </summary>
    private Task<Message> ProcessMessageAsync(MessageSendParams messageSendParams, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<Message>(cancellationToken);
        }

        var userText = GetTextFromMessage(messageSendParams.Message);

        Console.WriteLine($"[Calculator Agent] Received expression: {userText}");

        try
        {
            var result = EvaluateExpression(userText);
            var responseText = $"{userText} = {result}";

            var responseMessage = new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = responseText }]
            };

            Console.WriteLine($"[Calculator Agent] Calculated result: {responseText}");

            return Task.FromResult(responseMessage);
        }
        catch (Exception ex)
        {
            var errorText = $"Sorry, I couldn't calculate '{userText}'. Error: {ex.Message}. Please try a simple expression like '5 + 3' or '10 * 2'.";

            var errorMessage = new Message
            {
                Role = MessageRole.Agent,
                MessageId = Guid.NewGuid().ToString(),
                ContextId = messageSendParams.Message.ContextId,
                Parts = [new TextPart { Text = errorText }]
            };

            Console.WriteLine($"[Calculator Agent] Error: {ex.Message}");

            return Task.FromResult(errorMessage);
        }
    }

    /// <summary>
    /// Retrieves the agent card information for the Calculator Agent.
    /// </summary>
    private Task<AgentCard> GetAgentCardAsync(string agentUrl, CancellationToken cancellationToken)
    {
        if (cancellationToken.IsCancellationRequested)
        {
            return Task.FromCanceled<AgentCard>(cancellationToken);
        }

        return Task.FromResult(new AgentCard
        {
            Name = "Simple Calculator Agent",
            Description = "A basic calculator that can perform addition, subtraction, multiplication, and division. Send math expressions like '5 + 3' or '10 * 2'.",
            Url = agentUrl,
            Version = "1.0.0",
            DefaultInputModes = ["text"],
            DefaultOutputModes = ["text"],
            Capabilities = new AgentCapabilities { Streaming = true }
        });
    }

    /// <summary>
    /// Helper method to extract text from a message.
    /// </summary>
    private static string GetTextFromMessage(Message message)
    {
        var textPart = message.Parts.OfType<TextPart>().FirstOrDefault();
        return textPart?.Text ?? "";
    }

    /// <summary>
    /// Evaluates a simple math expression.
    /// Supports +, -, *, / operations with decimal numbers.
    /// </summary>
    private static double EvaluateExpression(string expression)
    {
        // Clean up the expression
        expression = expression.Trim();

        // Use regex to parse simple expressions like "5 + 3" or "10.5 * 2"
        var pattern = @"^\s*(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)\s*$";
        var match = Regex.Match(expression, pattern);

        if (!match.Success)
        {
            throw new ArgumentException("Please use format like '5 + 3' or '10.5 * 2'. I support +, -, *, / operations.");
        }

        var leftOperand = double.Parse(match.Groups[1].Value);
        var operation = match.Groups[2].Value;
        var rightOperand = double.Parse(match.Groups[3].Value);

        return operation switch
        {
            "+" => leftOperand + rightOperand,
            "-" => leftOperand - rightOperand,
            "*" => leftOperand * rightOperand,
            "/" => rightOperand == 0 ? throw new DivideByZeroException("Cannot divide by zero") : leftOperand / rightOperand,
            _ => throw new ArgumentException($"Unsupported operation: {operation}")
        };
    }
}
