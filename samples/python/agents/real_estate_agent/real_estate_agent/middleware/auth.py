import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/a2a/") and request.url.path != "/.well-known/agent.json":
            api_key_header = request.headers.get("authorization")
            expected_api_key = os.environ.get("API_KEY")

            if not expected_api_key:
                # This is a server configuration error. Log it and return an error.
                return Response(status_code=500, content="Internal Server Error: API Key not configured.")

            if not api_key_header or not api_key_header.startswith("Bearer "):
                return Response(status_code=401, content="Unauthorized")

            submitted_key = api_key_header.removeprefix("Bearer ")
            if not secrets.compare_digest(submitted_key, expected_api_key):
                return Response(status_code=401, content="Unauthorized")
        
        response = await call_next(request)
        return response