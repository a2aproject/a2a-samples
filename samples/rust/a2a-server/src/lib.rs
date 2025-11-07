//! # A2A Server
//!
//! HTTP server framework for building Agent2Agent (A2A) protocol agents in Rust.
//!
//! This crate provides:
//!
//! - `AgentExecutor` trait: Define your agent's logic
//! - `A2AServer`: HTTP server built on Axum
//! - `TaskStore` trait: Persist tasks and message history
//! - `InMemoryTaskStore`: Simple in-memory task storage
//!
//! ## Quick Start
//!
//! ```rust,ignore
//! use a2a_server::{A2AServer, executor::{AgentExecutor, RequestContext, EventQueue}, store::InMemoryTaskStore};
//! use a2a_core::types::{AgentCard, AgentCapabilities, AgentSkill, Message};
//! use async_trait::async_trait;
//! use std::sync::Arc;
//!
//! // 1. Implement your agent
//! struct MyAgent;
//!
//! #[async_trait]
//! impl AgentExecutor for MyAgent {
//!     async fn execute(&self, context: RequestContext, event_queue: EventQueue) -> anyhow::Result<()> {
//!         // Your agent logic here
//!         let response = Message::agent_text("Hello!");
//!         event_queue.send_message(response).await?;
//!
//!         let task = a2a_core::types::Task::new(context.task_id).complete();
//!         event_queue.send_completed(task).await?;
//!         Ok(())
//!     }
//!
//!     async fn cancel(&self, _context: RequestContext) -> anyhow::Result<()> {
//!         Ok(())
//!     }
//! }
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     // 2. Create your agent card
//!     let agent_card = AgentCard {
//!         name: "My Agent".to_string(),
//!         description: Some("A simple agent".to_string()),
//!         url: "http://localhost:9999".to_string(),
//!         version: "1.0.0".to_string(),
//!         capabilities: AgentCapabilities::default(),
//!         skills: vec![],
//!         // ... other fields
//!     };
//!
//!     // 3. Create and run the server
//!     let server = A2AServer::new(
//!         agent_card,
//!         Arc::new(MyAgent),
//!         Arc::new(InMemoryTaskStore::new()),
//!     );
//!
//!     server.run().await
//! }
//! ```

pub mod executor;
pub mod handler;
pub mod server;
pub mod store;

// Re-export commonly used types
pub use executor::{AgentEvent, AgentExecutor, AgentExecutorRef, EventQueue, RequestContext};
pub use server::A2AServer;
pub use store::{InMemoryTaskStore, TaskStore, TaskStoreRef};
