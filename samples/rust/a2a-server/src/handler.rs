use crate::executor::{AgentEvent, EventQueue, RequestContext};
use crate::store::TaskStoreRef;
use a2a_core::jsonrpc::{
    JsonRpcError, JsonRpcRequest, JsonRpcResponse, RequestId, TaskIdParams, TaskQueryParams,
    TaskSendParams,
};
use a2a_core::types::{Artifact, Message, Task, TaskState};
use std::sync::Arc;
use tokio::sync::mpsc;

use crate::executor::AgentExecutorRef;

/// Request handler for A2A JSON-RPC requests
pub struct RequestHandler {
    executor: AgentExecutorRef,
    task_store: TaskStoreRef,
}

impl RequestHandler {
    pub fn new(executor: AgentExecutorRef, task_store: TaskStoreRef) -> Self {
        Self {
            executor,
            task_store,
        }
    }

    /// Handle a JSON-RPC request
    pub async fn handle(&self, request: JsonRpcRequest) -> JsonRpcResponse {
        let id = request.id.clone().unwrap_or(RequestId::Null);

        match request.method.as_str() {
            "message/send" => self.handle_message_send(request, id).await,
            "tasks/get" => self.handle_task_get(request, id).await,
            "tasks/cancel" => self.handle_task_cancel(request, id).await,
            _ => JsonRpcResponse::error(
                id,
                JsonRpcError::method_not_found(format!("Method not found: {}", request.method)),
            ),
        }
    }

    async fn handle_message_send(
        &self,
        request: JsonRpcRequest,
        id: RequestId,
    ) -> JsonRpcResponse {
        // Parse parameters
        let params: TaskSendParams = match request.params {
            Some(params) => match serde_json::from_value(params) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        id,
                        JsonRpcError::invalid_params(format!("Invalid parameters: {}", e)),
                    )
                }
            },
            None => {
                return JsonRpcResponse::error(
                    id,
                    JsonRpcError::invalid_params("Missing parameters"),
                )
            }
        };

        // Create task
        let mut task = Task::new(params.id.clone());

        // Store initial message
        if let Err(e) = self.task_store.store_message(&task.id, params.message.clone()).await {
            return JsonRpcResponse::error(
                id,
                JsonRpcError::internal_error(format!("Failed to store message: {}", e)),
            );
        }

        // Store task
        if let Err(e) = self.task_store.store_task(task.clone()).await {
            return JsonRpcResponse::error(
                id,
                JsonRpcError::internal_error(format!("Failed to store task: {}", e)),
            );
        }

        // Get history
        let history = self
            .task_store
            .get_history(&task.id)
            .await
            .unwrap_or_default();

        // Create context
        let context = RequestContext {
            task_id: params.id.clone(),
            session_id: params.session_id.clone(),
            message: params.message.clone(),
            history,
        };

        // Create event queue
        let (tx, mut rx) = mpsc::unbounded_channel();
        let event_queue = EventQueue::new(tx);

        // Clone executor and task store for the async task
        let executor = Arc::clone(&self.executor);
        let task_store = Arc::clone(&self.task_store);
        let task_id = params.id.clone();

        // Execute agent in background
        tokio::spawn(async move {
            if let Err(e) = executor.execute(context, event_queue).await {
                tracing::error!("Agent execution failed: {}", e);
            }

            // Process events
            while let Some(event) = rx.recv().await {
                match event {
                    AgentEvent::Message(msg) => {
                        // Store message
                        if let Err(e) = task_store.store_message(&task_id, msg.clone()).await {
                            tracing::error!("Failed to store message: {}", e);
                        }

                        // Update task with artifact
                        if let Ok(Some(mut task)) = task_store.get_task(&task_id).await {
                            let artifact = message_to_artifact(msg);
                            task = task.with_artifact(artifact);
                            if let Err(e) = task_store.update_task(task).await {
                                tracing::error!("Failed to update task: {}", e);
                            }
                        }
                    }
                    AgentEvent::StatusUpdate(updated_task) => {
                        if let Err(e) = task_store.update_task(updated_task).await {
                            tracing::error!("Failed to update task: {}", e);
                        }
                    }
                    AgentEvent::Completed(completed_task) => {
                        if let Err(e) = task_store.update_task(completed_task).await {
                            tracing::error!("Failed to update task: {}", e);
                        }
                        break;
                    }
                    AgentEvent::Failed(error) => {
                        if let Ok(Some(mut task)) = task_store.get_task(&task_id).await {
                            task.status.state = TaskState::Failed;
                            if let Err(e) = task_store.update_task(task).await {
                                tracing::error!("Failed to update task: {}", e);
                            }
                        }
                        tracing::error!("Task failed: {}", error);
                        break;
                    }
                }
            }
        });

        // Wait a bit for the task to be updated
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        // Get updated task
        task = self
            .task_store
            .get_task(&params.id)
            .await
            .unwrap_or(Some(task))
            .unwrap();

        JsonRpcResponse::success(id, serde_json::to_value(&task).unwrap())
    }

    async fn handle_task_get(&self, request: JsonRpcRequest, id: RequestId) -> JsonRpcResponse {
        let params: TaskQueryParams = match request.params {
            Some(params) => match serde_json::from_value(params) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        id,
                        JsonRpcError::invalid_params(format!("Invalid parameters: {}", e)),
                    )
                }
            },
            None => {
                return JsonRpcResponse::error(
                    id,
                    JsonRpcError::invalid_params("Missing parameters"),
                )
            }
        };

        match self.task_store.get_task(&params.base.id).await {
            Ok(Some(task)) => JsonRpcResponse::success(id, serde_json::to_value(&task).unwrap()),
            Ok(None) => {
                JsonRpcResponse::error(id, JsonRpcError::task_not_found("Task not found"))
            }
            Err(e) => JsonRpcResponse::error(
                id,
                JsonRpcError::internal_error(format!("Failed to get task: {}", e)),
            ),
        }
    }

    async fn handle_task_cancel(&self, request: JsonRpcRequest, id: RequestId) -> JsonRpcResponse {
        let params: TaskIdParams = match request.params {
            Some(params) => match serde_json::from_value(params) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        id,
                        JsonRpcError::invalid_params(format!("Invalid parameters: {}", e)),
                    )
                }
            },
            None => {
                return JsonRpcResponse::error(
                    id,
                    JsonRpcError::invalid_params("Missing parameters"),
                )
            }
        };

        // Get task
        let mut task = match self.task_store.get_task(&params.id).await {
            Ok(Some(task)) => task,
            Ok(None) => {
                return JsonRpcResponse::error(id, JsonRpcError::task_not_found("Task not found"))
            }
            Err(e) => {
                return JsonRpcResponse::error(
                    id,
                    JsonRpcError::internal_error(format!("Failed to get task: {}", e)),
                )
            }
        };

        // Update task status
        task.status.state = TaskState::Canceled;

        // Store updated task
        if let Err(e) = self.task_store.update_task(task.clone()).await {
            return JsonRpcResponse::error(
                id,
                JsonRpcError::internal_error(format!("Failed to update task: {}", e)),
            );
        }

        // Call executor cancel
        let history = self
            .task_store
            .get_history(&params.id)
            .await
            .unwrap_or_default();

        let context = RequestContext {
            task_id: params.id.clone(),
            session_id: None,
            message: Message::new("system").with_text("cancel"),
            history,
        };

        if let Err(e) = self.executor.cancel(context).await {
            tracing::error!("Failed to cancel task: {}", e);
        }

        JsonRpcResponse::success(id, serde_json::to_value(&task).unwrap())
    }
}

/// Helper function to convert a message to an artifact
fn message_to_artifact(message: Message) -> Artifact {
    Artifact {
        name: Some(format!("{} message", message.role)),
        description: None,
        parts: message.parts,
        index: None,
        append: None,
        metadata: None,
        last_chunk: Some(true),
    }
}
