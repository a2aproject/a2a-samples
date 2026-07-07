import json

from pathlib import Path
from typing import Any

import uvicorn

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from a2a.utils.signing import create_agent_card_signer
from agent_executor import (
    SignedAgentExecutor,
)
from cryptography.hazmat.primitives import asymmetric, serialization
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Route


def create_public_private_keys() -> tuple[str, str]:
    """Generate EC private and public key pair as PEM-encoded strings."""
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode('utf-8')
    )
    return private_pem, public_pem


# Generate a private, public key pair
private_key, public_key = create_public_private_keys()

# Save public key to a file
key_id = 'my-key'
keys = {key_id: public_key}
with Path('public_keys.json').open('w') as f:
    json.dump(keys, f, indent=2)

skill = AgentSkill(
    id='reminder',
    name='Verification Reminder',
    description='Reminds the user to verify the Agent Card.',
    tags=['verify me'],
    examples=['Verify me!'],
)

extended_skill = AgentSkill(
    id='reminder-please',
    name='Verification Reminder Please!',
    description='Politely reminds user to verify the Agent Card.',
    tags=['verify me', 'pretty please', 'extended'],
    examples=['Verify me, pretty please! :)', 'Please verify me.'],
)

public_agent_card = AgentCard(
    name='Signed Agent',
    description='An Agent that is signed',
    icon_url='http://localhost:9999/',
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

extended_agent_card = AgentCard(
    name='Signed Agent - Extended Edition',
    description='The full-featured signed agent for authenticated users.',
    icon_url='http://localhost:9999/',
    version='1.0.1',
    default_input_modes=['text'],
    default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC',
            url='http://localhost:9999',
        )
    ],
    skills=[
        skill,
        extended_skill,
    ],
)

# Create singer function which will be used for AgentCard signing
signer = create_agent_card_signer(
    signing_key=private_key,
    protected_header={
        'kid': key_id,
        'alg': 'ES256',
        'jku': 'http://localhost:9999/public_keys.json',
    },
)


async def async_signer(card: AgentCard) -> AgentCard:
    """Sign the public agent card."""
    return signer(card)


async def async_extended_signer(card: AgentCard, _: Any) -> AgentCard:
    """Sign the extended agent card."""
    return signer(card)


request_handler = DefaultRequestHandler(
    agent_executor=SignedAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=public_agent_card,
    extended_agent_card=extended_agent_card,
    extended_card_modifier=async_extended_signer,
)

routes = []
routes.extend(create_agent_card_routes(public_agent_card, card_modifier=async_signer))
routes.extend(create_jsonrpc_routes(request_handler, '/'))

app = Starlette(routes=routes)
# Expose the public key for verification purposes
# Contents of public_keys.json will be fetched on the client side during AgentCard signatures verification
app.routes.append(
    Route(
        '/public_keys.json',
        endpoint=FileResponse('public_keys.json'),
        methods=['GET'],
    )
)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=9999)
