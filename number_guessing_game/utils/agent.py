"""utils.agent
Thin façade combining transport and helper modules into an easy-to-use
:class:`ToyA2AAgent` class suitable for small demos or tests.
"""

from __future__ import annotations

import threading
import time
import uuid
import json
from typing import Any, Dict
from urllib import request, error

from .transport import JSONRPC_VERSION, build_handler
from .card import make_agent_card
from .helpers import create_text_task, get_first_text_part

# ---------------------------------------------------------------------------
# Default message handler (echo)
# ---------------------------------------------------------------------------


def _handle_message_send(params: Dict[str, Any], tasks: Dict[str, Any]):
    """Fallback message handler that echoes back the first text part."""

    message = params.get("message", {})
    context_id = message.get("contextId")
    text = get_first_text_part(message) or ""
    return create_text_task(
        text,
        tasks,
        context_id=context_id,
        metadata=params.get("configuration"),
    )


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------


class ToyA2AAgent:
    """A minimal blocking-until-KeyboardInterrupt A2A agent."""

    def __init__(
        self,
        name: str,
        listen_port: int,
        peer_port: int,
        *,
        message_handler=_handle_message_send,
        agent_card: Dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.listen_port = listen_port
        self.peer_port = peer_port
        self._tasks: Dict[str, Any] = {}

        # Agent card ----------------------------------------------------
        self._agent_card = agent_card or make_agent_card(name, listen_port)

        # HTTP server ---------------------------------------------------
        handler_cls = build_handler(self._agent_card, self._tasks, message_handler)
        from http.server import HTTPServer  # local import to avoid at module import

        self._httpd = HTTPServer(("localhost", listen_port), handler_cls)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the HTTP server in a background thread."""

        self._thread.start()
        print(f"{self.name} listening on http://localhost:{self.listen_port}")

    # ------------------------------------------------------------------
    # Peer communication helpers
    # ------------------------------------------------------------------

    def _build_jsonrpc_message(self, text: str, *, msg_id: str | None = None) -> bytes:
        """Return encoded JSON-RPC payload for a simple user text message."""

        if msg_id is None:
            msg_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "contextId": str(uuid.uuid4()),
                    "messageId": str(uuid.uuid4()),
                    "parts": [{"kind": "text", "text": text}],
                }
            },
        }
        return json.dumps(payload).encode()

    def fetch_agent_card(self, peer_port: int):
        """Retrieve the peer's AgentCard from ``/.well-known/agent.json``."""

        url = f"http://localhost:{peer_port}/.well-known/agent.json"
        try:
            with request.urlopen(url) as resp:
                return json.loads(resp.read().decode())
        except error.URLError as exc:
            print(f"[{self.name}] Could not fetch agent card from {url}: {exc.reason}")
            return None

    def send_message_to(self, peer_port: int, text: str):
        """Send a one-shot ``message/send`` to *peer_port*."""

        url = f"http://localhost:{peer_port}/a2a/v1"
        data = self._build_jsonrpc_message(text)
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except error.URLError as exc:
            print(f"[{self.name}] Could not reach peer at {url}: {exc.reason}")
            return None

    def send_message(self, text: str):
        """Shortcut that targets this agent's *peer_port*."""

        return self.send_message_to(self.peer_port, text)

    # ------------------------------------------------------------------
    # Context manager helpers
    # ------------------------------------------------------------------

    def __enter__(self):  # pragma: no cover
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover
        self._httpd.shutdown()
        self._thread.join()


# ---------------------------------------------------------------------------
# Convenience runners
# ---------------------------------------------------------------------------


def run_agent_forever(agent: "ToyA2AAgent") -> None:
    """Start *agent* and block until interrupted by the user."""

    agent.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print(f"Stopping {agent.name}…")


def run_agent(name: str, listen_port: int, peer_port: int, greeting: str | None = None):
    """Utility to spin up an agent from the CLI with an optional greeting."""

    agent = ToyA2AAgent(name, listen_port, peer_port)
    run_agent_forever(agent) 