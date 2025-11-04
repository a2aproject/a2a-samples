package ai.koog.example.simplejoke

import ai.koog.a2a.exceptions.A2AUnsupportedOperationException
import ai.koog.a2a.model.MessageSendParams
import ai.koog.a2a.server.agent.AgentExecutor
import ai.koog.a2a.server.session.RequestContext
import ai.koog.a2a.server.session.SessionEventProcessor
import ai.koog.agents.a2a.core.MessageA2AMetadata
import ai.koog.agents.a2a.core.toA2AMessage
import ai.koog.agents.a2a.core.toKoogMessage
import ai.koog.prompt.dsl.prompt
import ai.koog.prompt.executor.clients.google.GoogleLLMClient
import ai.koog.prompt.executor.clients.google.GoogleModels
import ai.koog.prompt.executor.llms.MultiLLMPromptExecutor
import ai.koog.prompt.llm.LLMProvider
import ai.koog.prompt.message.Message
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

/**
 * This is a simple example of an agent executor that wraps LLM calls using prompt executor to generate jokes.
 */
class SimpleJokeAgentExecutor : AgentExecutor {
    private val promptExecutor =
        MultiLLMPromptExecutor(
//        LLMProvider.OpenAI to OpenAILLMClient(System.getenv("OPENAI_API_KEY")),
//        LLMProvider.Anthropic to AnthropicLLMClient(System.getenv("ANTHROPIC_API_KEY")),
            LLMProvider.Google to GoogleLLMClient(System.getenv("GOOGLE_API_KEY")),
        )

    @OptIn(ExperimentalUuidApi::class)
    override suspend fun execute(
        context: RequestContext<MessageSendParams>,
        eventProcessor: SessionEventProcessor,
    ) {
        val userMessage = context.params.message

        if (context.task != null || !userMessage.referenceTaskIds.isNullOrEmpty()) {
            throw A2AUnsupportedOperationException("This agent doesn't support tasks")
        }

        // Save incoming message to the current context
        context.messageStorage.save(userMessage)

        // Load all messages from the current context
        val contextMessages = context.messageStorage.getAll().map { it.toKoogMessage() }

        val prompt =
            prompt("joke-generation") {
                system {
                    +"You are an assistant helping user to generate jokes"
                }

                // Append current message context
                messages(contextMessages)
            }

        // Get a response from the LLM
        val responseMessage =
            promptExecutor
                .execute(prompt, GoogleModels.Gemini2_5Flash)
                .single()
                .let { message ->
                    message as? Message.Assistant ?: throw IllegalStateException("Unexpected message type: $message")
                }.toA2AMessage(
                    a2aMetadata =
                        MessageA2AMetadata(
                            messageId = Uuid.random().toString(),
                            contextId = context.contextId,
                        ),
                )

        // Save the response to the current context
        context.messageStorage.save(responseMessage)

        // Reply with message
        eventProcessor.sendMessage(responseMessage)
    }
}
