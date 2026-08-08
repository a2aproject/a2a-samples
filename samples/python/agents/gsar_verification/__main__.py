"""Serves the reservation-lookup agent over real A2A.

Same wiring pattern as a2a-samples' own helloworld __main__.py, trimmed to
one agent card.
"""

import sys

import uvicorn

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_executor import ReservationLookupAgentExecutor
from starlette.applications import Starlette


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

skill = AgentSkill(
    id='reservation_lookup',
    name='Reservation Lookup',
    description='Looks up a reservation by ID and reports its details.',
    input_modes=['text/plain'],
    output_modes=['text/plain'],
    tags=['a2a', 'gsar-example'],
    examples=['ZFA04Y'],
)

agent_card = AgentCard(
    name='Reservation Lookup Agent',
    description='Looks up a reservation and reports its details.',
    version='0.0.1',
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC', url=f'http://127.0.0.1:{PORT}', protocol_version='1.0'
        )
    ],
    skills=[skill],
)

request_handler = DefaultRequestHandler(
    agent_executor=ReservationLookupAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

routes = []
routes.extend(create_agent_card_routes(agent_card))
routes.extend(create_jsonrpc_routes(request_handler, '/'))
app = Starlette(routes=routes)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=PORT)
