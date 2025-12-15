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
from agent_executor import (
    HelloWorldAgentExecutor,  # type: ignore[import-untyped]
)
from cryptography.hazmat.primitives import asymmetric, serialization


if __name__ == '__main__':
    # Generate key pair
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    public_key = private_key.public_key()

    # Save public key to a file
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open('public_key.pem', 'wb') as f:
        f.write(pem)

    # --8<-- [start:AgentSkill]
    skill = AgentSkill(
        id='reminder',
        name='Verification Reminder',
        description='Reminds the User to verify the Agent Card',
        tags=['verify me'],
        examples=['verify me'],
    )
    # --8<-- [end:AgentSkill]

    extended_skill = AgentSkill(
        id='reminder-please',
        name='Returns a SUPER Hello World',
        description='A more enthusiastic greeting, only for authenticated users.',
        tags=['hello world', 'super', 'extended'],
        examples=['super hi', 'give me a super hello'],
    )

    # --8<-- [start:AgentCard]
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Signed Agent',
        description='An Agent which is signed',
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )
    # --8<-- [end:AgentCard]

    # This will be the authenticated extended agent card
    # It includes the additional 'extended_skill'
    specific_extended_agent_card = public_agent_card.model_copy(
        update={
            'name': 'Hello World Agent - Extended Edition',  # Different name for clarity
            'description': 'The full-featured hello world agent for authenticated users.',
            'version': '1.0.1',  # Could even be a different version
            # Capabilities and other fields like url, default_input_modes, default_output_modes,
            # supports_authenticated_extended_card are inherited from public_agent_card unless specified here.
            'skills': [
                skill,
                extended_skill,
            ],  # Both skills for the extended card
        }
    )

    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    signer = create_agent_card_signer(
        signing_key=private_key,
        protected_header={
            'kid': 'my-key',
            'alg': 'ES256',
        },
    )
    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
        extended_agent_card=specific_extended_agent_card,
        extended_card_modifier=lambda card, ctx: signer(card),
    )

    uvicorn.run(server.build(), host='0.0.0.0', port=9999)
