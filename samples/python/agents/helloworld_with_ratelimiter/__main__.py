import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent_executor import (
    HelloWorldAgentExecutor,  # type: ignore[import-untyped]
)
from ratelimiter_ext import RateLimitingExtension, TokenBucketLimiter


if __name__ == '__main__':
    # Initialize rate limiter for enforcement (always active)
    # Token bucket allows burst traffic up to 20 requests (10 * 2.0 multiplier)
    # then maintains steady 10 requests per minute
    rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)

    # Initialize extension for communication (activated by client)
    # This allows clients to receive usage signals in responses
    rate_limit_extension = RateLimitingExtension()
    # --8<-- [start:AgentSkill]
    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )
    # --8<-- [end:AgentSkill]

    extended_skill = AgentSkill(
        id='super_hello_world',
        name='Returns a SUPER Hello World',
        description='A more enthusiastic greeting, only for authenticated users.',
        tags=['hello world', 'super', 'extended'],
        examples=['super hi', 'give me a super hello'],
    )

    # --8<-- [start:AgentCard]
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Hello World Agent with Rate Limiting',
        description='Hello world agent demonstrating A2A rate limiting extension',
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
            'name': 'Hello World Agent with Rate Limiting - Extended Edition',  # Different name for clarity
            'description': 'The full-featured rate-limited hello world agent for authenticated users.',
            'version': '1.0.1',  # Could even be a different version
            # Capabilities and other fields like url, default_input_modes,
            # default_output_modes, supports_authenticated_extended_card
            # are inherited from public_agent_card unless specified here.
            'skills': [
                skill,
                extended_skill,
            ],  # Both skills for the extended card
        }
    )

    # Add rate limiting extension to agent cards
    # This advertises that the agent can communicate rate limit usage signals
    public_agent_card = rate_limit_extension.add_to_card(public_agent_card)
    specific_extended_agent_card = rate_limit_extension.add_to_card(
        specific_extended_agent_card
    )

    # Create agent executor with rate limiting enforcement built-in
    # No wrapping needed - executor handles enforcement directly
    executor = HelloWorldAgentExecutor(
        rate_limiter=rate_limiter, rate_limit_extension=rate_limit_extension
    )

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
        extended_agent_card=specific_extended_agent_card,
    )

    # Bind to 0.0.0.0 to allow external connections in containerized environment
    uvicorn.run(server.build(), host='0.0.0.0', port=9999)  # noqa: S104
