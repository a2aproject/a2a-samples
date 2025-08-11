import asyncio
import traceback

from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    SendStreamingMessageRequest,
    TextPart,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/get-token')
async def get_token():
    """Executes the gcloud command to get an identity token."""
    try:
        proc = await asyncio.create_subprocess_exec(
            'gcloud',
            'auth',
            'print-identity-token',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(
                f'gcloud command failed: {stderr.decode("utf-8").strip()}'
            )
        token = stdout.decode('utf-8').strip()
        return JSONResponse(content={'token': token})
    except FileNotFoundError:
        return JSONResponse(
            content={
                'error': 'gcloud command not found. Please ensure the Google Cloud SDK is installed and in your PATH.'
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


async def stream_proxy(response_stream, client_to_close):
    """A generator that yields data from the response_stream and ensures the httpx client
    is closed upon completion or error.
    """
    try:
        async for result in response_stream:
            if result.root.result:
                yield f'data: {result.root.result.model_dump_json()}\n\n'
    except Exception as e:
        print(f'Error during stream generation: {e}')
        traceback.print_exc()
    finally:
        await client_to_close.aclose()


@app.post('/')
async def proxy_request(request: Request):
    """Proxies requests to the A2A agent. It handles two cases:
    1. Fetching the agent card (a simple POST request).
    2. Sending a message and streaming the response (a POST request with a message body).
    """
    try:
        data = await request.json()
        url = data.get('url')
        headers = data.get('headers', {})
        body = data.get('body', {})
        headers.pop('host', None)

        # Case 1: Send a message and stream the response
        if 'message' in body and body.get('message'):
            # For streaming, we manage the client lifecycle manually to keep it open
            # for the duration of the stream.
            httpx_client = httpx.AsyncClient(timeout=30, headers=headers)

            card_resolver = A2ACardResolver(httpx_client, url)
            card = await card_resolver.get_agent_card()
            client = A2AClient(httpx_client, agent_card=card)

            parts = body.get('message', {}).get('parts', [])
            if not parts or not parts[0].get('text'):
                raise ValueError('Message text not found in request')
            message_text = parts[0]['text']

            message = Message(
                role='user',
                parts=[TextPart(text=message_text)],
                message_id=str(uuid4()),
                context_id=body.get('context_id'),
            )
            payload = MessageSendParams(id=str(uuid4()), message=message)
            response_stream = client.send_message_streaming(
                SendStreamingMessageRequest(id=str(uuid4()), params=payload)
            )

            # The stream_proxy generator will handle closing the client
            return StreamingResponse(
                stream_proxy(response_stream, httpx_client),
                media_type='text/event-stream',
            )

        # Case 2: Fetch the agent card
        # For a single request, 'async with' is the safest way to manage the client
        async with httpx.AsyncClient(
            timeout=30, headers=headers
        ) as httpx_client:
            card_resolver = A2ACardResolver(httpx_client, url)
            card = await card_resolver.get_agent_card()
            return JSONResponse(content=card.model_dump())

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={'error': str(e)}, status_code=500)


app.mount('/', StaticFiles(directory='gui', html=True), name='static')
