use a2a_core::types::{Message, Task};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Trait for task storage
#[async_trait]
pub trait TaskStore: Send + Sync {
    /// Store a task
    async fn store_task(&self, task: Task) -> anyhow::Result<()>;

    /// Get a task by ID
    async fn get_task(&self, id: &str) -> anyhow::Result<Option<Task>>;

    /// Update a task
    async fn update_task(&self, task: Task) -> anyhow::Result<()>;

    /// Delete a task
    async fn delete_task(&self, id: &str) -> anyhow::Result<()>;

    /// Store a message in the task history
    async fn store_message(&self, task_id: &str, message: Message) -> anyhow::Result<()>;

    /// Get message history for a task
    async fn get_history(&self, task_id: &str) -> anyhow::Result<Vec<Message>>;
}

/// In-memory implementation of TaskStore
#[derive(Default)]
pub struct InMemoryTaskStore {
    tasks: Arc<RwLock<HashMap<String, Task>>>,
    history: Arc<RwLock<HashMap<String, Vec<Message>>>>,
}

impl InMemoryTaskStore {
    pub fn new() -> Self {
        Self {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            history: Arc::new(RwLock::new(HashMap::new())),
        }
    }
}

#[async_trait]
impl TaskStore for InMemoryTaskStore {
    async fn store_task(&self, task: Task) -> anyhow::Result<()> {
        let mut tasks = self.tasks.write().await;
        tasks.insert(task.id.clone(), task);
        Ok(())
    }

    async fn get_task(&self, id: &str) -> anyhow::Result<Option<Task>> {
        let tasks = self.tasks.read().await;
        Ok(tasks.get(id).cloned())
    }

    async fn update_task(&self, task: Task) -> anyhow::Result<()> {
        let mut tasks = self.tasks.write().await;
        tasks.insert(task.id.clone(), task);
        Ok(())
    }

    async fn delete_task(&self, id: &str) -> anyhow::Result<()> {
        let mut tasks = self.tasks.write().await;
        tasks.remove(id);
        Ok(())
    }

    async fn store_message(&self, task_id: &str, message: Message) -> anyhow::Result<()> {
        let mut history = self.history.write().await;
        history
            .entry(task_id.to_string())
            .or_insert_with(Vec::new)
            .push(message);
        Ok(())
    }

    async fn get_history(&self, task_id: &str) -> anyhow::Result<Vec<Message>> {
        let history = self.history.read().await;
        Ok(history.get(task_id).cloned().unwrap_or_default())
    }
}

/// Type alias for Arc-wrapped task store
pub type TaskStoreRef = Arc<dyn TaskStore>;
