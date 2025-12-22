import json
from pathlib import Path

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.utils.signing import create_agent_card_signer
from cryptography.hazmat.primitives import asymmetric, serialization
from starlette.responses import FileResponse
from starlette.routing import Route

from agent_executor import (
    SignedAgentExecutor,
)

if __name__ == '__main__':
    # Generate a private, public key pair
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    public_key = private_key.public_key()

    # Save public key to a file
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    kid = 'my-key'
    keys = {kid: pem}
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
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        supports_authenticated_extended_card=True,
    )

    extended_agent_card = public_agent_card.model_copy(
        update={
            'name': 'Signed Agent - Extended Edition',
            'description': 'The full-featured signed agent for authenticated users.',
            'version': '1.0.1',
            'skills': [
                skill,
                extended_skill,
            ],
        }
    )

    request_handler = DefaultRequestHandler(
        agent_executor=SignedAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # Create singer function which will be used for AgentCard signing
    signer = create_agent_card_signer(
        signing_key=private_key,
        protected_header={
            'kid': kid,
            'alg': 'ES256',
            'jku': 'http://localhost:9999/public_keys.json',
        },
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
        card_modifier=signer,  # The signer function is used to sign the public Agent Card
        extended_agent_card=extended_agent_card,
        extended_card_modifier=lambda card, _: signer(
            card
        ),  # The signer function is also used to sign the extended Agent Card
    )

    app = server.build()
    # Expose the public key for verification purposes
    # Contents of public_keys.json will be fetched on the client side during AgentCard signatures verification
    app.routes.append(
        Route(
            '/public_keys.json',
            endpoint=FileResponse('public_keys.json'),
            methods=['GET'],
        )
    )
    uvicorn.run(app, host='127.0.0.1', port=9999)
