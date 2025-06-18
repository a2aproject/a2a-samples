import base64
import contextlib
import json
import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    AuthorizationCodeOAuthFlow,
    OAuth2SecurityScheme,
    OAuthFlows,
    SecurityScheme,
)
from adk_agent import create_agent  # type: ignore[import-not-found]
from adk_agent_executor import ADKAgentExecutor  # type: ignore[import-untyped]
from dotenv import load_dotenv
from google.adk.artifacts import (
    InMemoryArtifactService,  # type: ignore[import-untyped]
)
from google.adk.memory.in_memory_memory_service import (
    InMemoryMemoryService,  # type: ignore[import-untyped]
)
from google.adk.runners import Runner  # type: ignore[import-untyped]
from google.adk.sessions import (
    InMemorySessionService,  # type: ignore[import-untyped]
)
from starlette.applications import Starlette
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    SimpleUser,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route


load_dotenv()

logging.basicConfig()


class InsecureJWTAuthBackend(AuthenticationBackend):
    """An example implementation of a JWT-based authentication backend."""

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        # For illustrative purposes only: please validate your JWTs!
        with contextlib.suppress(Exception):
            auth_header = conn.headers['Authorization']
            jwt = auth_header.split('Bearer ')[1]
            jwt_claims = jwt.split('.')[1]
            missing_padding = len(jwt_claims) % 4
            if missing_padding:
                jwt_claims += '=' * (4 - missing_padding)
            payload = base64.urlsafe_b64decode(jwt_claims).decode('utf-8')
            parsed_payload = json.loads(payload)
            return AuthCredentials([]), SimpleUser(parsed_payload['sub'])
        return None


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10007)
def main(host: str, port: int):
    # Verify an API key is set.
    # Not required if using Vertex AI APIs.
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv(
        'GOOGLE_API_KEY'
    ):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and '
            'GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    skill = AgentSkill(
        id='check_availability',
        name='Check Availability',
        description="Checks a user's availability for a time using their Google Calendar",
        tags=['calendar'],
        examples=['Am I free from 10am to 11am tomorrow?'],
    )

    # Define OAuth2 security scheme.
    OAUTH_SCHEME_NAME = 'CalendarGoogleOAuth'
    oauth_scheme = OAuth2SecurityScheme(
        type='oauth2',
        description='OAuth2 for Google Calendar API',
        flows=OAuthFlows(
            authorizationCode=AuthorizationCodeOAuthFlow(
                authorizationUrl='https://accounts.google.com/o/oauth2/auth',
                tokenUrl='https://oauth2.googleapis.com/token',
                scopes={
                    'https://www.googleapis.com/auth/calendar': 'Access Google Calendar'
                },
            )
        ),
    )

    # Update the AgentCard to include the 'securitySchemes' and 'security' fields.
    agent_card = AgentCard(
        name='Calendar Agent',
        description="An agent that can manage a user's calendar",
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        securitySchemes={OAUTH_SCHEME_NAME: SecurityScheme(root=oauth_scheme)},
        # Declare that this scheme is required to use the agent's skills
        security=[
            {OAUTH_SCHEME_NAME: ['https://www.googleapis.com/auth/calendar']}
        ],
    )

    adk_agent = create_agent(
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    )
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    agent_executor = ADKAgentExecutor(runner, agent_card)

    async def handle_auth(request: Request) -> PlainTextResponse:
        await agent_executor.on_auth_callback(
            str(request.query_params.get('state')), str(request.url)
        )
        return PlainTextResponse('Authentication successful.')

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    routes = a2a_app.routes()
    routes.append(
        Route(
            path='/authenticate',
            methods=['GET'],
            endpoint=handle_auth,
        )
    )
    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(
                AuthenticationMiddleware, backend=InsecureJWTAuthBackend()
            )
        ],
    )

    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
