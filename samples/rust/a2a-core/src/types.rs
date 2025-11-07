use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Task state within the A2A protocol
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum TaskState {
    Submitted,
    Working,
    InputRequired,
    Completed,
    Canceled,
    Failed,
    Unknown,
}

/// Authentication schemes and credentials for an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentAuthentication {
    /// List of supported authentication schemes
    pub schemes: Vec<String>,
    /// Credentials for authentication (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub credentials: Option<String>,
}

/// Capabilities of an agent
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct AgentCapabilities {
    /// Indicates if the agent supports streaming responses
    #[serde(skip_serializing_if = "Option::is_none")]
    pub streaming: Option<bool>,
    /// Indicates if the agent supports push notifications
    #[serde(skip_serializing_if = "Option::is_none")]
    pub push_notifications: Option<bool>,
    /// Indicates if the agent supports state transition history
    #[serde(skip_serializing_if = "Option::is_none")]
    pub state_transition_history: Option<bool>,
}

/// Provider or organization behind an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentProvider {
    /// Name of the organization providing the agent
    pub organization: String,
    /// URL associated with the agent provider
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
}

/// A specific skill or capability offered by an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentSkill {
    /// Unique identifier for the skill
    pub id: String,
    /// Human-readable name of the skill
    pub name: String,
    /// Optional description of the skill
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// Optional list of tags for categorization
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    /// Optional list of example inputs or use cases
    #[serde(skip_serializing_if = "Option::is_none")]
    pub examples: Option<Vec<String>>,
    /// Optional list of input modes supported
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input_modes: Option<Vec<String>>,
    /// Optional list of output modes supported
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output_modes: Option<Vec<String>>,
}

/// Metadata card for an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentCard {
    /// Name of the agent
    pub name: String,
    /// Optional description of the agent
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// Base URL endpoint for interacting with the agent
    pub url: String,
    /// Information about the provider of the agent
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<AgentProvider>,
    /// Version identifier for the agent or its API
    pub version: String,
    /// Optional URL pointing to the agent's documentation
    #[serde(skip_serializing_if = "Option::is_none")]
    pub documentation_url: Option<String>,
    /// Capabilities supported by the agent
    pub capabilities: AgentCapabilities,
    /// Authentication details required to interact with the agent
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authentication: Option<AgentAuthentication>,
    /// Default input modes supported by the agent
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_input_modes: Option<Vec<String>>,
    /// Default output modes supported by the agent
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default_output_modes: Option<Vec<String>>,
    /// List of specific skills offered by the agent
    pub skills: Vec<AgentSkill>,
}

/// Base structure for file content
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FileContentBase {
    /// Optional name of the file
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    /// Optional MIME type of the file content
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
}

/// File content as base64-encoded bytes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileContentBytes {
    #[serde(flatten)]
    pub base: FileContentBase,
    /// File content encoded as a Base64 string
    pub bytes: String,
}

/// File content as a URI
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileContentUri {
    #[serde(flatten)]
    pub base: FileContentBase,
    /// URI pointing to the file content
    pub uri: String,
}

/// File content (either bytes or URI-based)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum FileContent {
    Bytes(FileContentBytes),
    Uri(FileContentUri),
}

/// A part of a message or artifact
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Part {
    /// Type identifier for this part
    #[serde(skip_serializing_if = "Option::is_none", rename = "type")]
    pub part_type: Option<String>,
    /// Text content for text parts
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text: Option<String>,
    /// File content for file parts
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file: Option<FileContent>,
    /// Structured data content for data parts
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<HashMap<String, serde_json::Value>>,
    /// Optional metadata associated with this part
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

impl Part {
    /// Create a text part
    pub fn text(text: impl Into<String>) -> Self {
        Self {
            part_type: Some("text".to_string()),
            text: Some(text.into()),
            file: None,
            data: None,
            metadata: None,
        }
    }
}

/// An output or intermediate file from a task
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Artifact {
    /// Optional name for the artifact
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    /// Optional description of the artifact
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// Constituent parts of the artifact
    pub parts: Vec<Part>,
    /// Optional index for ordering artifacts
    #[serde(skip_serializing_if = "Option::is_none")]
    pub index: Option<i32>,
    /// Indicates if this artifact content should append to previous content
    #[serde(skip_serializing_if = "Option::is_none")]
    pub append: Option<bool>,
    /// Optional metadata associated with the artifact
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, serde_json::Value>>,
    /// Indicates if this is the last chunk of data for this artifact
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_chunk: Option<bool>,
}

/// Status of a task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStatus {
    pub state: TaskState,
}

/// An A2A task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub status: TaskStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub artifacts: Option<Vec<Artifact>>,
}

impl Task {
    /// Create a new task with the given ID
    pub fn new(id: String) -> Self {
        Self {
            id,
            status: TaskStatus {
                state: TaskState::Working,
            },
            artifacts: None,
        }
    }

    /// Mark task as completed
    pub fn complete(mut self) -> Self {
        self.status.state = TaskState::Completed;
        self
    }

    /// Mark task as failed
    pub fn fail(mut self) -> Self {
        self.status.state = TaskState::Failed;
        self
    }

    /// Add an artifact to the task
    pub fn with_artifact(mut self, artifact: Artifact) -> Self {
        self.artifacts
            .get_or_insert_with(Vec::new)
            .push(artifact);
        self
    }
}

/// A message in the A2A protocol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub parts: Vec<Part>,
}

impl Message {
    /// Create a new message with the given role
    pub fn new(role: impl Into<String>) -> Self {
        Self {
            role: role.into(),
            parts: Vec::new(),
        }
    }

    /// Add a text part to the message
    pub fn with_text(mut self, text: impl Into<String>) -> Self {
        self.parts.push(Part::text(text));
        self
    }

    /// Add a part to the message
    pub fn with_part(mut self, part: Part) -> Self {
        self.parts.push(part);
        self
    }

    /// Create an agent message with text
    pub fn agent_text(text: impl Into<String>) -> Self {
        Self::new("agent").with_text(text)
    }

    /// Create a user message with text
    pub fn user_text(text: impl Into<String>) -> Self {
        Self::new("user").with_text(text)
    }
}

/// History of a task
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TaskHistory {
    /// List of messages in chronological order
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message_history: Option<Vec<Message>>,
}

/// Event for task status updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStatusUpdateEvent {
    /// ID of the task being updated
    pub id: String,
    /// New status of the task
    pub status: TaskStatus,
    /// Indicates if this is the final update for the task
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_: Option<bool>,
    /// Optional metadata associated with this update event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

/// Event for task artifact updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskArtifactUpdateEvent {
    /// ID of the task being updated
    pub id: String,
    /// New or updated artifact for the task
    pub artifact: Artifact,
    /// Indicates if this is the final update for the task
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_: Option<bool>,
    /// Optional metadata associated with this update event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}
