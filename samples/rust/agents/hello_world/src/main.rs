use a2a_core::types::{AgentCapabilities, AgentCard, AgentSkill, Message, Task};
use a2a_server::{
    executor::{AgentExecutor, EventQueue, RequestContext},
    store::InMemoryTaskStore,
    A2AServer,
};
use async_trait::async_trait;
use std::sync::Arc;

/// Hello World Agent
///
/// A simple agent that responds with "Hello World" to any message.
struct HelloWorldAgent;

#[async_trait]
impl AgentExecutor for HelloWorldAgent {
    async fn execute(
        &self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> anyhow::Result<()> {
        tracing::info!("Executing Hello World agent for task: {}", context.task_id);

        // Extract the user's message
        let user_message = context
            .message
            .parts
            .iter()
            .find_map(|part| part.text.as_ref())
            .unwrap_or(&"".to_string())
            .to_lowercase();

        tracing::info!("User message: {}", user_message);

        // Generate response based on input
        let response_text = if user_message.contains("super") {
            "🌟 SUPER HELLO WORLD! 🌟"
        } else {
            "Hello World"
        };

        // Create agent response message
        let response = Message::agent_text(response_text);

        // Send the message event
        event_queue.send_message(response).await?;

        // Mark task as completed
        let completed_task = Task::new(context.task_id).complete();
        event_queue.send_completed(completed_task).await?;

        tracing::info!("Hello World agent execution completed");

        Ok(())
    }

    async fn cancel(&self, context: RequestContext) -> anyhow::Result<()> {
        tracing::warn!("Cancel requested for task: {}", context.task_id);
        // For this simple agent, we don't have long-running operations to cancel
        Ok(())
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into()),
        )
        .init();

    tracing::info!("🦀 Starting Hello World A2A Agent");

    // Define agent skills
    let basic_skill = AgentSkill {
        id: "hello_world".to_string(),
        name: "Returns hello world".to_string(),
        description: Some("Just returns hello world".to_string()),
        tags: Some(vec!["hello world".to_string(), "greeting".to_string()]),
        examples: Some(vec![
            "hi".to_string(),
            "hello world".to_string(),
            "say hello".to_string(),
        ]),
        input_modes: None,
        output_modes: None,
    };

    let super_skill = AgentSkill {
        id: "super_hello_world".to_string(),
        name: "Returns a SUPER Hello World".to_string(),
        description: Some(
            "A more enthusiastic greeting with sparkles ✨".to_string(),
        ),
        tags: Some(vec![
            "hello world".to_string(),
            "super".to_string(),
            "greeting".to_string(),
        ]),
        examples: Some(vec![
            "super hi".to_string(),
            "give me a super hello".to_string(),
            "super hello world".to_string(),
        ]),
        input_modes: None,
        output_modes: None,
    };

    // Create agent card
    let agent_card = AgentCard {
        name: "Hello World Agent (Rust)".to_string(),
        description: Some("A simple hello world agent written in Rust 🦀".to_string()),
        url: "http://localhost:9999".to_string(),
        provider: None,
        version: "1.0.0".to_string(),
        documentation_url: Some(
            "https://github.com/google-a2a/a2a-samples/tree/main/samples/rust".to_string(),
        ),
        capabilities: AgentCapabilities {
            streaming: Some(false),
            push_notifications: Some(false),
            state_transition_history: Some(false),
        },
        authentication: None,
        default_input_modes: Some(vec!["text".to_string()]),
        default_output_modes: Some(vec!["text".to_string()]),
        skills: vec![basic_skill, super_skill],
    };

    // Create the agent executor
    let executor = Arc::new(HelloWorldAgent);

    // Create the task store
    let task_store = Arc::new(InMemoryTaskStore::new());

    // Create and run the server
    let server = A2AServer::new(agent_card, executor, task_store)
        .with_host("0.0.0.0")
        .with_port(9999);

    server.run().await?;

    Ok(())
}
