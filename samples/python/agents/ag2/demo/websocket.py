import json
import os
from pathlib import Path
import socket
import sys
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    # Load .env from current directory or any parent directory (e.g., repo root)
    # so OPENAI_API_KEY is available without manually setting it per terminal.
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except Exception:
    pass

# Add parent directory to path to import AG2 core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the AG2 sample client (reused without modification)
import fastapi_codegen_a2a_client as demo
from autogen.a2a import A2aRemoteAgent


APP_HOST = os.getenv("AG2_WS_UI_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("AG2_WS_UI_PORT", "9000"))
REVIEWER_URL = os.getenv("A2A_REVIEWER_URL", "http://localhost:8000")
UI_HTML_PATH = Path(__file__).parent / "ui.html"
ASSETS_DIR = Path(__file__).parent / "assets"

app = FastAPI(title="AG2 A2A WebSocket UI")

# Static UI assets (PNG frames, backgrounds). If you add images into ./assets,
# they will be available at http://<host>:<port>/assets/<filename>
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), check_dir=False), name="assets")


def _probe_reviewer(reviewer_url: str) -> tuple[bool, str]:
    """Best-effort connectivity check (TCP) to help demos/debugging.

    Some A2A servers may return 404 for GET /, so HTTP-based checks can be
    misleading. A TCP connection is enough to confirm the service is up.
    """

    parsed = urlparse(reviewer_url)
    host = parsed.hostname
    if not host:
        return False, "Invalid reviewer URL"

    if parsed.port:
        port = parsed.port
    else:
        port = 443 if parsed.scheme == "https" else 80

    try:
        with socket.create_connection((host, port), timeout=2):
            return True, f"TCP OK to {host}:{port}"
    except Exception as e:
        return False, f"TCP connect failed to {host}:{port} ({e})"


def _reply_to_text(reply: object) -> str:
    if isinstance(reply, dict):
        return str(reply.get("content") or "")
    return str(reply or "")


async def _run_codegen_then_review_loop(
    *,
    codegen_agent: object,
    reviewer_url: str,
    prompt: str,
    send: callable,
) -> str:
    max_rounds = int(os.getenv("AG2_MAX_ROUNDS", "3"))
    reviewer_agent = A2aRemoteAgent(url=reviewer_url, name="ReviewerAgent")

    await send({"type": "chat", "name": "User", "role": "user", "content": prompt})

    current_prompt = prompt
    last_code = ""
    for round_num in range(1, max_rounds + 1):
        await send({"type": "status", "message": f"Round {round_num}/{max_rounds}: generating code…"})

        # Generate code locally using the CodeGenAgent.
        code_reply = await codegen_agent.a_generate_reply(messages=[{"role": "user", "content": current_prompt}])
        code_text = _reply_to_text(code_reply).strip()
        last_code = code_text
        await send({"type": "chat", "name": "CodeGenAgent", "role": "assistant", "content": code_text})

        await send({"type": "status", "message": "Sending code to ReviewerAgent over A2A (mypy)…"})
        review_prompt = (
            "Please run mypy on the following single-file FastAPI app. "
            "Return ONLY the mypy output. If there are no issues, return exactly: No issues found.\n\n"
            "```python\n"
            f"{code_text}\n"
            "```"
        )

        review_reply = await reviewer_agent.a_generate_reply(messages=[{"role": "user", "content": review_prompt}])
        review_text = _reply_to_text(review_reply).strip()
        await send({"type": "chat", "name": "ReviewerAgent", "role": "assistant", "content": review_text})

        if "No issues found." in review_text:
            await send({"type": "status", "message": "Reviewer reports no issues. Done."})
            return code_text

        current_prompt = (
            "Please fix the code to address these mypy issues. "
            "Return the full corrected code as a single file, code only:\n\n"
            f"{review_text}"
        )

    await send({"type": "status", "message": "Reached max rounds; returning last generated code."})
    return last_code


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = UI_HTML_PATH.read_text(encoding="utf-8")
    html = html.replace("window.__REVIEWER_URL__", f"{REVIEWER_URL!r}")
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()

    async def send(payload: dict) -> None:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    try:
        raw = await websocket.receive_text()
        payload = json.loads(raw)
        prompt = (payload.get("prompt") or "").strip()

        if not prompt:
            await send({"type": "error", "error": "No prompt provided."})
            return

        if not os.getenv("OPENAI_API_KEY"):
            await send(
                {
                    "type": "error",
                    "error": "OPENAI_API_KEY is not set. Create a .env with OPENAI_API_KEY=... and run again.",
                }
            )
            return

        await send({"type": "status", "message": f"Reviewer (A2A): {REVIEWER_URL}"})
        ok, detail = _probe_reviewer(REVIEWER_URL)
        await send(
            {
                "type": "status",
                "message": f"Reviewer reachable: {'YES' if ok else 'NO'} — {detail}",
            }
        )
        if not ok:
            await send(
                {
                    "type": "error",
                    "error": "Reviewer agent is not reachable. Start a2a_python_reviewer.py on :8000 and try again.",
                }
            )
            return
        await send(
            {
                "type": "status",
                "message": "Using existing sample: fastapi_codegen_a2a_client.py",
            }
        )
        await send(
            {
                "type": "status",
                "message": "Starting A2A chat (CodeGenAgent ↔ ReviewerAgent)…",
            }
        )

        # Run multi-round code generation + review loop with WebSocket updates
        code = await _run_codegen_then_review_loop(
            codegen_agent=demo.codegen_agent,
            reviewer_url=REVIEWER_URL,
            prompt=prompt,
            send=send,
        )

        await send({"type": "result", "code": code or "(no code found)"})

    except WebSocketDisconnect:
        return
    except Exception as e:
        await send({"type": "error", "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
