//! # A2A Core
//!
//! Core types and utilities for the Agent2Agent (A2A) Protocol.
//!
//! This crate provides the foundational types and structures needed to implement
//! A2A agents and clients, including:
//!
//! - Protocol types: `AgentCard`, `Task`, `Message`, `Artifact`, etc.
//! - JSON-RPC types: Request, response, and error structures
//! - Error handling types
//!
//! ## Example
//!
//! ```rust
//! use a2a_core::types::{AgentCard, AgentCapabilities, AgentSkill};
//!
//! let skill = AgentSkill {
//!     id: "hello".to_string(),
//!     name: "Hello World".to_string(),
//!     description: Some("Returns a greeting".to_string()),
//!     tags: None,
//!     examples: Some(vec!["hi".to_string(), "hello".to_string()]),
//!     input_modes: None,
//!     output_modes: None,
//! };
//!
//! let card = AgentCard {
//!     name: "Hello Agent".to_string(),
//!     description: Some("A simple greeting agent".to_string()),
//!     url: "http://localhost:9999".to_string(),
//!     provider: None,
//!     version: "1.0.0".to_string(),
//!     documentation_url: None,
//!     capabilities: AgentCapabilities {
//!         streaming: Some(true),
//!         ..Default::default()
//!     },
//!     authentication: None,
//!     default_input_modes: Some(vec!["text".to_string()]),
//!     default_output_modes: Some(vec!["text".to_string()]),
//!     skills: vec![skill],
//! };
//! ```

pub mod error;
pub mod jsonrpc;
pub mod types;

// Re-export commonly used types
pub use error::{A2AError, Result};
pub use jsonrpc::{
    ErrorCode, JsonRpcError, JsonRpcRequest, JsonRpcResponse, RequestId, TaskIdParams,
    TaskQueryParams, TaskSendParams, JSONRPC_VERSION,
};
pub use types::{
    AgentCapabilities, AgentCard, AgentSkill, Artifact, Message, Part, Task, TaskState,
    TaskStatus,
};
