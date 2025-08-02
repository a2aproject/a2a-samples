"""utils.transport
HTTP transport and JSON-RPC request handling helpers used by the toy
A2A demo.  This module centralises all network-facing code so that the rest
of the project can focus on domain logic.
"""

from __future__ import annotations

import http.server
import json
from enum import IntEnum
from http import HTTPStatus
from typing import Any, Dict, Callable

# Public constants -----------------------------------------------------------

JSONRPC_VERSION = "2.0"

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class JSONRPCErrorCode(IntEnum):
    """Enumeration of JSON-RPC error codes used in this demo."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602

    OPERATION_NOT_SUPPORTED = -32004
    CONTENT_TYPE_NOT_SUPPORTED = -32005
    TASK_NOT_FOUND = -32001


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

MessageHandler = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]

# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------


def build_handler(
    agent_card: Dict[str, Any],
    tasks: Dict[str, Any],
    message_handler: MessageHandler,
):  # noqa: C901
    """Return a *BaseHTTPRequestHandler* subclass bound to supplied state."""

    class A2AHandler(http.server.BaseHTTPRequestHandler):
        # Disable default noisy logging ------------------------------------------------
        def log_message(  # type: ignore[override]
            self, fmt: str, *args: Any
        ) -> None:  # noqa: D401  (stdlib name)
            return

        # Helper: send JSON ----------------------------------------------------
        def _send_json(self, obj: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(obj).encode()
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        # Helper: send error with JSON-RPC envelope ---------------------------
        def _send_error(
            self,
            req_id: Any,
            code: JSONRPCErrorCode | int,
            message: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self._send_json(
                {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": req_id,
                    "error": {"code": code, "message": message},
                },
                status,
            )

        # ------------------------------------------------------------------
        # HTTP verbs
        # ------------------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/.well-known/agent.json":
                self._send_json(agent_card)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        # ------------------------------------------------------------------
        # RPC helpers
        # ------------------------------------------------------------------
        def _rpc_message_send(self, req: Dict[str, Any], req_id: Any) -> None:
            """Handle the ``message/send`` JSON-RPC method."""

            msg_obj = req.get("params", {}).get("message", {})

            # Validate mandatory fields per A2A spec ----------------------
            mandatory_fields = ["kind", "role", "messageId", "parts"]
            if any(field not in msg_obj for field in mandatory_fields):
                self._send_error(
                    req_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    "Invalid params: missing required message fields",
                )
                return

            if msg_obj.get("kind") != "message":
                self._send_error(
                    req_id,
                    JSONRPCErrorCode.INVALID_PARAMS,
                    "Invalid params: 'kind' must be 'message'",
                )
                return

            parts = msg_obj.get("parts", [])
            text_parts = [p for p in parts if p.get("kind") == "text"]
            if not text_parts:
                self._send_error(
                    req_id,
                    JSONRPCErrorCode.CONTENT_TYPE_NOT_SUPPORTED,
                    "Incompatible content types",
                )
                return

            # Delegate to caller-provided message handler -----------------
            result = message_handler(req.get("params", {}), tasks)
            self._send_json({"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": result})

        def _rpc_tasks_get(self, req: Dict[str, Any], req_id: Any) -> None:
            """Handle the ``tasks/get`` JSON-RPC method."""

            task_id = req.get("params", {}).get("id")
            task = tasks.get(task_id)
            if task:
                self._send_json({"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": task})
            else:
                self._send_error(req_id, JSONRPCErrorCode.TASK_NOT_FOUND, "Task not found")

        def _rpc_unsupported(self, method: Any, req_id: Any) -> None:
            """Handle unknown or unimplemented RPC methods."""

            if isinstance(method, str) and (
                method.startswith("message/") or method.startswith("tasks/")
            ):
                err_code, err_msg = (
                    JSONRPCErrorCode.OPERATION_NOT_SUPPORTED,
                    "This operation is not supported",
                )
            else:
                err_code, err_msg = (
                    JSONRPCErrorCode.METHOD_NOT_FOUND,
                    "Method not found",
                )

            self._send_error(req_id, err_code, err_msg)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/a2a/v1":
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            try:
                raw_len = int(self.headers.get("Content-Length", "0"))
                payload = self.rfile.read(raw_len)
                req = json.loads(payload)
            except Exception:  # noqa: BLE001 (broad for robustness)
                self._send_error(
                    None,
                    JSONRPCErrorCode.PARSE_ERROR,
                    "Invalid JSON payload",
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            method = req.get("method")
            req_id = req.get("id")

            if method == "message/send":
                self._rpc_message_send(req, req_id)
            elif method == "tasks/get":
                self._rpc_tasks_get(req, req_id)
            else:
                self._rpc_unsupported(method, req_id)

    return A2AHandler 