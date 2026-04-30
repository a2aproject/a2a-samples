# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module defining the Starlette application and A2A server configuration."""

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent_executor import (
    WeatherReportingPoetExecutor,  # type: ignore[import-untyped]
)

# Define the skill that this agent specializes in
skill = AgentSkill(
    id='weather_reporting_poet',
    name='Weather Reporting Poet',
    description='Poet for latest weather updates',
    tags=['poet', 'weather'],
    examples=[
        'How is the weather in Warsaw, Poland',
        'How is the weather in Hyderabad, India',
    ],
)

# Define the public-facing Agent Card
agent_card = AgentCard(
    name='Weather Reporting Poet',
    description='Weather reporting Poet',
    version='1.0.0',
    default_input_modes=['text'],
    default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC',
            url='http://localhost:9999',
        )
    ],
    skills=[skill],
)

# Set up the default A2A request handler with necessary components
request_handler = DefaultRequestHandler(
    agent_card=agent_card,
    agent_executor=WeatherReportingPoetExecutor(),
    task_store=InMemoryTaskStore(),
)


async def health_check(request) -> JSONResponse:
    """Simple health check endpoint."""
    return JSONResponse({'message': 'ok!'})


# Build the Starlette routes
app_routes = []
app_routes.extend(create_agent_card_routes(agent_card=agent_card))
app_routes.extend(
    create_jsonrpc_routes(request_handler=request_handler, rpc_url='/')
)
app_routes.append(Route('/health', endpoint=health_check))

if __name__ == '__main__':
    # Initialize and start the Starlette application
    server = Starlette(routes=app_routes, debug=True)
    uvicorn.run(server, host='127.0.0.1', port=9999)

