from fastapi import FastAPI, Request
import uuid
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HOST_AGENT_URL = "http://localhost:8001/"  # HostAgent 서버의 A2A 엔드포인트

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/message")
async def send_message(request: Request):
    data = await request.json()
    #session_id = data.get("session_id", "default")
    query = data.get("query", {})
    user_id = data.get("user_id", "guest")
    app_name = data.get("app_name", "default")
    metadata = data.get("metadata", {})

    session_id = str(uuid.uuid4())

    message_id = str(uuid.uuid4())
    message = {
        "messageId": message_id,
        "role": "user",
        "parts": [
            {
                "text": query
            }
        ],
        "metadata": {
            "user_id": user_id,
            "app_name" : app_name,
            "session_id": session_id
        }
    }

    payload = {
        "jsonrpc": "2.0",
        "id" : session_id,
        "method": "message/stream",
        "params": {
            "message": message,
        }
    }

    async def event_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                HOST_AGENT_URL,
                json=payload,
                headers={
                    "accept": "text/event-stream",
                    "connection": "keep-alive",
                    "content-type": "application/json",
                }
            ) as response:
                async for line in response.aiter_lines():
                    logger.info(f"line: {line}")
                    yield f"data: {line}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")