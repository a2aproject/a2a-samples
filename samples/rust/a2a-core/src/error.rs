use thiserror::Error;

/// Core A2A errors
#[derive(Debug, Error)]
pub enum A2AError {
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Task not found: {0}")]
    TaskNotFound(String),

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Invalid parameters: {0}")]
    InvalidParams(String),

    #[error("Method not found: {0}")]
    MethodNotFound(String),

    #[error("Internal error: {0}")]
    InternalError(String),

    #[error("Custom error: {0}")]
    Custom(String),
}

pub type Result<T> = std::result::Result<T, A2AError>;
