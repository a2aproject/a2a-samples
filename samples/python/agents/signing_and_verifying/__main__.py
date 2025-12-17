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
from agent_executor import (
    SignedAgentExecutor,  # type: ignore[import-untyped]
)
from cryptography.hazmat.primitives import asymmetric, serialization
from starlette.responses import FileResponse
from starlette.routing import Route


if __name__ == "__main__":
    # --8<-- [start:KeyPair]
    private_key = asymmetric.ec.generate_private_key(asymmetric.ec.SECP256R1())
    public_key = private_key.public_key()
    # --8<-- [end:KeyPair]

    # Save public key to a file
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    kid = "my-key"
    keys = {}
    try:
        with Path("public_keys.json").open() as f:
            keys = json.load(f)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        print("Warning: public_keys.json is not valid JSON. Starting fresh.")

    keys[kid] = pem

    with Path("public_keys.json").open("w") as f:
        json.dump(keys, f, indent=2)

    # --8<-- [start:AgentSkill]
    skill = AgentSkill(
        id="reminder",
        name="Verification Reminder",
        description="Reminds the user to verify the Agent Card.",
        tags=["verify me"],
        examples=["Verify me!"],
    )
    # --8<-- [end:AgentSkill]

    extended_skill = AgentSkill(
        id="reminder-please",
        name="Verification Reminder Please!",
        description="Politely reminds user to verify the Agent Card.",
        tags=["verify me", "pretty please", "extended"],
        examples=["Verify me, pretty please! :)", "Please verify me."],
    )

    # --8<-- [start:AgentCard]
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name="Signed Agent",
        description="An Agent that is signed",
        url="http://localhost:9999/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )
    # --8<-- [end:AgentCard]

    # This will be the authenticated extended agent card
    # It includes the additional 'extended_skill'
    extended_agent_card = public_agent_card.model_copy(
        update={
            "name": "Signed Agent - Extended Edition",
            "description": "The full-featured signed agent for authenticated users.",
            "version": "1.0.1",  # Could even be a different version
            # Capabilities and other fields like url, default_input_modes, default_output_modes,
            # supports_authenticated_extended_card are inherited from public_agent_card unless specified here.
            "skills": [
                skill,
                extended_skill,
            ],  # Both skills for the extended card
        }
    )

    # --8<-- [start:DefaultRequestHandler]
    request_handler = DefaultRequestHandler(
        agent_executor=SignedAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    # --8<-- [end:DefaultRequestHandler]

    signer = create_agent_card_signer(
        signing_key=private_key,
        protected_header={
            "kid": "my-key",
            "alg": "ES256",
            "jku": "http://localhost:9999/public_keys.json",
        },
    )

    # --8<-- [start:A2AStarletteApplication]
    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
        card_modifier=signer,
        extended_agent_card=extended_agent_card,
        extended_card_modifier=lambda card, _: signer(card),
    )
    # --8<-- [end:A2AStarletteApplication]

    app = server.build()
    app.routes.append(
        Route(
            "/public_keys.json",
            endpoint=FileResponse("public_keys.json"),
            methods=["GET"],
        )
    )
    uvicorn.run(app, host="127.0.0.1", port=9999)
