"""Blueprint Governed Agent — A2A server entry point.

Demonstrates AI Design Blueprint governance principles via the A2A protocol:
- Explicit approval before destructive actions (Blueprint P8)
- Perceptible background work via streaming state updates (Blueprint P5)
- Mid-task steering via cancellation support (Blueprint P7)
"""

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentInterface, AgentSkill
from starlette.applications import Starlette
from starlette.routing import Route

from agent_executor import GovernedFileAgent

HOST = "127.0.0.1"
PORT = 9999
BASE_URL = f"http://{HOST}:{PORT}"

skill = AgentSkill(
    id="governed_file_ops",
    name="Governed File Operations",
    description=(
        "Manages files with explicit approval gates before destructive actions, "
        "real-time progress streaming, and mid-task cancellation support. "
        "Implements AI Design Blueprint governance principles."
    ),
    tags=["blueprint", "governance", "file-management"],
    examples=["delete /tmp/test.txt"],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)

# Declare the JSON-RPC interface so clients can discover the transport.
jsonrpc_interface = AgentInterface(
    url=f"{BASE_URL}/",
    protocol_binding="JSONRPC",
    protocol_version="1.0",
)

agent_card = AgentCard(
    name="Blueprint Governed Agent",
    description=(
        "File agent with Blueprint governance — approval gates before destructive "
        "actions, real-time status streaming, and mid-task steering support."
    ),
    version="0.1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[skill],
    supported_interfaces=[jsonrpc_interface],
)

task_store = InMemoryTaskStore()
executor = GovernedFileAgent()
request_handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=task_store,
    agent_card=agent_card,
)

routes: list[Route] = [
    *create_agent_card_routes(agent_card),
    *create_jsonrpc_routes(request_handler, rpc_url="/"),
]

app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
