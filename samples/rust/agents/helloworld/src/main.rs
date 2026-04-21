//! A2A Hello World agent in Rust.
//!
//! Implements the Agent-to-Agent (A2A) protocol over JSON-RPC 2.0 using axum.
//! Exposes an Agent Card at `/.well-known/agent.json` and handles
//! `message/send` and `tasks/get` JSON-RPC methods.
//!
//! Run with:
//!   cargo run
//!
//! Test with:
//!   curl -s http://localhost:9999/.well-known/agent.json | jq .

use axum::{
    Json, Router,
    extract::State,
    routing::{get, post},
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// A2A protocol types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AgentSkill {
    id: String,
    name: String,
    description: String,
    tags: Vec<String>,
    examples: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AgentCapabilities {
    streaming: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AgentCard {
    name: String,
    description: String,
    url: String,
    version: String,
    default_input_modes: Vec<String>,
    default_output_modes: Vec<String>,
    capabilities: AgentCapabilities,
    skills: Vec<AgentSkill>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Part {
    #[serde(rename = "type")]
    part_type: String,
    text: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    role: String,
    parts: Vec<Part>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TaskStatus {
    state: String,
    message: Option<Message>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct Artifact {
    name: String,
    parts: Vec<ArtifactPart>,
    index: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct ArtifactPart {
    #[serde(rename = "type")]
    part_type: String,
    text: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Task {
    id: String,
    context_id: String,
    status: TaskStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    artifacts: Option<Vec<Artifact>>,
}

// ---------------------------------------------------------------------------
// JSON-RPC 2.0 envelope types
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct JsonRpcRequest {
    jsonrpc: String,
    id: Value,
    method: String,
    #[serde(default)]
    params: Value,
}

#[derive(Debug, Serialize)]
struct JsonRpcResponse {
    jsonrpc: String,
    id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize)]
struct JsonRpcError {
    code: i32,
    message: String,
}

impl JsonRpcResponse {
    fn ok(id: Value, result: Value) -> Self {
        Self { jsonrpc: "2.0".into(), id, result: Some(result), error: None }
    }

    fn err(id: Value, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: None,
            error: Some(JsonRpcError { code, message: message.into() }),
        }
    }
}

// ---------------------------------------------------------------------------
// Shared state
// ---------------------------------------------------------------------------

type TaskStore = Arc<Mutex<HashMap<String, Task>>>;

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async fn agent_card() -> Json<AgentCard> {
    Json(AgentCard {
        name: "Hello World Agent (Rust)".into(),
        description: "A minimal A2A agent implemented in Rust. Responds with a greeting.".into(),
        url: "http://localhost:9999".into(),
        version: "0.1.0".into(),
        default_input_modes: vec!["text".into()],
        default_output_modes: vec!["text".into()],
        capabilities: AgentCapabilities { streaming: false },
        skills: vec![AgentSkill {
            id: "hello_world".into(),
            name: "Hello World".into(),
            description: "Returns a friendly Rust greeting".into(),
            tags: vec!["hello".into(), "greeting".into()],
            examples: vec!["hi".into(), "hello".into(), "greet me".into()],
        }],
    })
}

async fn rpc_handler(
    State(store): State<TaskStore>,
    Json(req): Json<JsonRpcRequest>,
) -> Json<JsonRpcResponse> {
    if req.jsonrpc != "2.0" {
        return Json(JsonRpcResponse::err(req.id, -32600, "Invalid JSON-RPC version"));
    }

    let resp = match req.method.as_str() {
        "message/send" => handle_message_send(&store, req.id, req.params),
        "tasks/get" => handle_tasks_get(&store, req.id, req.params),
        _ => JsonRpcResponse::err(req.id, -32601, "Method not found"),
    };

    Json(resp)
}

fn handle_message_send(store: &TaskStore, id: Value, params: Value) -> JsonRpcResponse {
    let task_id = params
        .get("id")
        .and_then(Value::as_str)
        .map(str::to_owned)
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    let context_id = params
        .get("contextId")
        .and_then(Value::as_str)
        .map(str::to_owned)
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    let artifact = Artifact {
        name: "greeting".into(),
        parts: vec![ArtifactPart {
            part_type: "text".into(),
            text: "Hello from Rust A2A! \u{1F980}".into(),
        }],
        index: 0,
    };

    let task = Task {
        id: task_id.clone(),
        context_id,
        status: TaskStatus { state: "completed".into(), message: None },
        artifacts: Some(vec![artifact]),
    };

    let result = serde_json::to_value(&task).unwrap();
    store.lock().unwrap().insert(task_id, task);
    JsonRpcResponse::ok(id, result)
}

fn handle_tasks_get(store: &TaskStore, id: Value, params: Value) -> JsonRpcResponse {
    let task_id = match params.get("id").and_then(Value::as_str) {
        Some(t) => t.to_owned(),
        None => return JsonRpcResponse::err(id, -32602, "Missing required param: id"),
    };

    let guard = store.lock().unwrap();
    match guard.get(&task_id) {
        Some(task) => JsonRpcResponse::ok(id, serde_json::to_value(task).unwrap()),
        None => JsonRpcResponse::err(id, -32001, "Task not found"),
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    let store: TaskStore = Arc::new(Mutex::new(HashMap::new()));

    let app = Router::new()
        .route("/.well-known/agent.json", get(agent_card))
        .route("/", post(rpc_handler))
        .with_state(store);

    let addr = "0.0.0.0:9999";
    println!("A2A Hello World agent listening on http://{addr}");
    println!("  Agent card : http://localhost:9999/.well-known/agent.json");
    println!("  RPC endpoint: http://localhost:9999/");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
