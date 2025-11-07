use a2a_core::types::{Message, Task};
use async_trait::async_trait;
use std::sync::Arc;
use tokio::sync::mpsc;

/// Events that can be emitted during agent execution
#[derive(Debug, Clone)]
pub enum AgentEvent {
    /// A message from the agent
    Message(Message),
    /// Task status update
    StatusUpdate(Task),
    /// Task completed
    Completed(Task),
    /// Task failed
    Failed(String),
}

/// Event queue for agent execution
pub struct EventQueue {
    sender: mpsc::UnboundedSender<AgentEvent>,
}

impl EventQueue {
    pub(crate) fn new(sender: mpsc::UnboundedSender<AgentEvent>) -> Self {
        Self { sender }
    }

    /// Enqueue an event
    pub async fn send(&self, event: AgentEvent) -> anyhow::Result<()> {
        self.sender
            .send(event)
            .map_err(|e| anyhow::anyhow!("Failed to send event: {}", e))
    }

    /// Send a message event
    pub async fn send_message(&self, message: Message) -> anyhow::Result<()> {
        self.send(AgentEvent::Message(message)).await
    }

    /// Send a status update event
    pub async fn send_status_update(&self, task: Task) -> anyhow::Result<()> {
        self.send(AgentEvent::StatusUpdate(task)).await
    }

    /// Send a completion event
    pub async fn send_completed(&self, task: Task) -> anyhow::Result<()> {
        self.send(AgentEvent::Completed(task)).await
    }

    /// Send a failure event
    pub async fn send_failed(&self, error: String) -> anyhow::Result<()> {
        self.send(AgentEvent::Failed(error)).await
    }
}

/// Context for agent execution
#[derive(Debug, Clone)]
pub struct RequestContext {
    /// Task ID
    pub task_id: String,
    /// Session ID (if provided)
    pub session_id: Option<String>,
    /// Incoming message
    pub message: Message,
    /// Message history
    pub history: Vec<Message>,
}

/// Trait for implementing agent executors
///
/// Implement this trait to create your custom agent logic.
///
/// # Example
///
/// ```rust,ignore
/// use a2a_server::executor::{AgentExecutor, RequestContext, EventQueue, AgentEvent};
/// use a2a_core::types::Message;
/// use async_trait::async_trait;
///
/// struct MyAgent;
///
/// #[async_trait]
/// impl AgentExecutor for MyAgent {
///     async fn execute(&self, context: RequestContext, event_queue: EventQueue) -> anyhow::Result<()> {
///         // Process the message
///         let response = Message::agent_text("Hello from my agent!");
///
///         // Send response
///         event_queue.send_message(response).await?;
///
///         // Mark as complete
///         let task = a2a_core::types::Task::new(context.task_id).complete();
///         event_queue.send_completed(task).await?;
///
///         Ok(())
///     }
///
///     async fn cancel(&self, context: RequestContext) -> anyhow::Result<()> {
///         // Handle cancellation
///         Ok(())
///     }
/// }
/// ```
#[async_trait]
pub trait AgentExecutor: Send + Sync {
    /// Execute the agent logic
    ///
    /// This method is called when a new task is received. The agent should:
    /// 1. Process the incoming message
    /// 2. Send events via the event queue (messages, status updates)
    /// 3. Send a completion or failure event when done
    async fn execute(
        &self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> anyhow::Result<()>;

    /// Cancel an ongoing task
    ///
    /// This method is called when a task cancellation is requested.
    async fn cancel(&self, context: RequestContext) -> anyhow::Result<()>;
}

/// Type alias for Arc-wrapped agent executor
pub type AgentExecutorRef = Arc<dyn AgentExecutor>;
