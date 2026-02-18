import os

from a2a.types import AgentCard
from auth0_api_python import ApiClient, ApiClientOptions
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse


api_client = ApiClient(
    ApiClientOptions(
        domain=os.getenv('HR_AUTH0_DOMAIN'),
        audience=os.getenv('HR_AGENT_AUTH0_AUDIENCE'),
    )
)


from collections.abc import Callable
from typing import Any

from auth0_api_python import ApiClient, ApiClientOptions
from starlette.responses import Response


api_client = ApiClient(
    ApiClientOptions(
        domain=os.getenv('HR_AUTH0_DOMAIN'),
        audience=os.getenv('HR_AGENT_AUTH0_AUDIENCE'),
    )
)


class OAuth2Middleware(BaseHTTPMiddleware):
    """Starlette middleware that authenticates A2A access using an OAuth2 bearer token."""

    def __init__(
        self,
        app: Starlette,
        agent_card: AgentCard | None = None,
        public_paths: list[str] | None = None,
    ) -> None:
        """Initialize the OAuth2 middleware."""
        super().__init__(app)
        self.agent_card = agent_card
        self.public_paths = set(public_paths or [])

        # Process the AgentCard to identify what (if any) Security Requirements are defined at the root of the
        # AgentCard, indicating agent-level authentication/authorization.

        # Use app state for this demonstration (simplicity)
        self.a2a_auth: dict[str, Any] = {}

        # Access the modern 'security' and 'security_schemes' fields
        # security is a list of dicts: [{'scheme_name': ['scope1', 'scope2']}]
        security = getattr(agent_card, 'security', [])

        if security and len(security) > 0:
            # We take the first requirement set defined in the card
            requirement = security[0]
            for scheme_name, scopes in requirement.items():
                # Store the scopes for the dispatch check
                self.a2a_auth = {
                    'scheme': scheme_name,
                    'required_scopes': scopes,
                }
                break

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Verify the authentication and authorization of the request."""
        path = request.url.path

        # Allow public paths and anonymous access
        if path in self.public_paths or not self.a2a_auth:
            return await call_next(request)

        # Authenticate the request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return self._unauthorized(
                'Missing or malformed Authorization header.', request
            )

        access_token = auth_header.split('Bearer ')[1]

        try:
            if self.a2a_auth:
                payload = await api_client.verify_access_token(
                    access_token=access_token
                )
                scopes = payload.get('scope', '').split()
                missing_scopes = [
                    s
                    for s in self.a2a_auth['required_scopes']
                    if s not in scopes
                ]
                if missing_scopes:
                    return self._forbidden(
                        f'Missing required scopes: {missing_scopes}', request
                    )

        except Exception as e:  # noqa: BLE001
            return self._forbidden(f'Authentication failed: {e}', request)

        return await call_next(request)

    def _forbidden(self, reason: str, request: Request) -> Response:
        """Return a forbidden response."""
        accept_header = request.headers.get('accept', '')
        if 'text/event-stream' in accept_header:
            return PlainTextResponse(
                f'error forbidden: {reason}',
                status_code=403,
                media_type='text/event-stream',
            )
        return JSONResponse(
            {'error': 'forbidden', 'reason': reason}, status_code=403
        )

    def _unauthorized(self, reason: str, request: Request) -> Response:
        """Return an unauthorized response."""
        accept_header = request.headers.get('accept', '')
        if 'text/event-stream' in accept_header:
            return PlainTextResponse(
                f'error unauthorized: {reason}',
                status_code=401,
                media_type='text/event-stream',
            )
        return JSONResponse(
            {'error': 'unauthorized', 'reason': reason}, status_code=401
        )
