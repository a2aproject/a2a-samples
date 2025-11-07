use crate::executor::AgentExecutorRef;
use crate::handler::RequestHandler;
use crate::store::TaskStoreRef;
use a2a_core::jsonrpc::{JsonRpcRequest, JsonRpcResponse};
use a2a_core::types::AgentCard;
use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use std::sync::Arc;
use tower_http::cors::CorsLayer;

/// A2A server state
#[derive(Clone)]
pub struct A2AServerState {
    agent_card: Arc<AgentCard>,
    handler: Arc<RequestHandler>,
}

/// A2A Server
pub struct A2AServer {
    agent_card: AgentCard,
    executor: AgentExecutorRef,
    task_store: TaskStoreRef,
    host: String,
    port: u16,
}

impl A2AServer {
    /// Create a new A2A server
    pub fn new(
        agent_card: AgentCard,
        executor: AgentExecutorRef,
        task_store: TaskStoreRef,
    ) -> Self {
        Self {
            agent_card,
            executor,
            task_store,
            host: "0.0.0.0".to_string(),
            port: 9999,
        }
    }

    /// Set the host address
    pub fn with_host(mut self, host: impl Into<String>) -> Self {
        self.host = host.into();
        self
    }

    /// Set the port
    pub fn with_port(mut self, port: u16) -> Self {
        self.port = port;
        self
    }

    /// Build and return the Axum router
    pub fn build_router(&self) -> Router {
        let handler = Arc::new(RequestHandler::new(
            Arc::clone(&self.executor),
            Arc::clone(&self.task_store),
        ));

        let state = A2AServerState {
            agent_card: Arc::new(self.agent_card.clone()),
            handler,
        };

        Router::new()
            .route("/", post(handle_jsonrpc))
            .route("/agent-card", get(handle_agent_card))
            .route("/health", get(handle_health))
            .with_state(state)
            .layer(CorsLayer::permissive())
    }

    /// Run the server
    pub async fn run(self) -> anyhow::Result<()> {
        let addr = format!("{}:{}", self.host, self.port);
        let listener = tokio::net::TcpListener::bind(&addr).await?;

        tracing::info!("🦀 A2A Server listening on http://{}", addr);
        tracing::info!("📋 Agent Card: {}", self.agent_card.name);
        tracing::info!("🔗 Agent URL: {}", self.agent_card.url);

        let router = self.build_router();

        axum::serve(listener, router).await?;

        Ok(())
    }
}

/// Handle JSON-RPC requests
async fn handle_jsonrpc(
    State(state): State<A2AServerState>,
    Json(request): Json<JsonRpcRequest>,
) -> Result<Json<JsonRpcResponse>, AppError> {
    tracing::debug!("Received JSON-RPC request: {:?}", request);

    let response = state.handler.handle(request).await;

    tracing::debug!("Sending JSON-RPC response: {:?}", response);

    Ok(Json(response))
}

/// Handle agent card requests
async fn handle_agent_card(
    State(state): State<A2AServerState>,
) -> Result<Json<AgentCard>, AppError> {
    Ok(Json((*state.agent_card).clone()))
}

/// Handle health check requests
async fn handle_health() -> &'static str {
    "OK"
}

/// Application error type
struct AppError(anyhow::Error);

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Internal server error: {}", self.0),
        )
            .into_response()
    }
}

impl<E> From<E> for AppError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        Self(err.into())
    }
}
