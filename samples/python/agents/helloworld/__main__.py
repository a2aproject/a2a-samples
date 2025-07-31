import datetime

import click
import uvicorn

from a2a.server.agent_execution import RequestContext
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


def create_dynamic_public_card(base_card: AgentCard) -> AgentCard:
    """Dynamically modifies the public agent card.

    This function is called for each request to the public card endpoint.
    It can be used to add dynamic information, like a timestamp.

    Args:
        base_card: The base agent card to use as a template.

    Returns:
        A new, dynamically generated AgentCard.
    """
    # Start with a copy of the base card to avoid modifying the original
    public_card = base_card.model_copy(deep=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Set the description directly to make the function more robust.
    # This avoids depending on the description from the base_card.
    public_card.description = f'Just a hello world agent (last updated: {now})'
    return public_card


def create_dynamic_extended_card(
    base_card: AgentCard, _context: RequestContext
) -> AgentCard:
    """Dynamically creates an extended agent card from a base card.

    This function is called for each request to the extended card endpoint,
    allowing the card to be customized based on the request context, such as
    authentication headers.

    Args:
        base_card: The public agent card to use as a template.
        _context: The server call context, containing request information.
            This parameter is intentionally unused in this example.

    Returns:
        A new, dynamically generated AgentCard.
    """
    # Start with a copy of the base card to avoid modifying the original
    extended_card = base_card.model_copy(deep=True)

    # Add the extended skill that is always present for authenticated users
    extended_skill = AgentSkill(
        id='super_hello_world',
        name='Returns a SUPER Hello World',
        description='A more enthusiastic greeting, only for authenticated users.',
        tags=['hello world', 'super', 'extended'],
        examples=['super hi', 'give me a super hello'],
    )
    extended_card.skills.append(extended_skill)

    # Update basic properties for the extended card
    extended_card.name = 'Hello World Agent - Extended Edition'
    extended_card.description = (
        'The full-featured hello world agent for authenticated users.'
    )
    extended_card.version = '1.0.1'

    return extended_card


@click.command()
@click.option(
    '--dynamic-public-card',
    is_flag=True,
    default=False,
    help='Enable dynamic public agent card.',
)
@click.option(
    '--enable-extended-card',
    is_flag=True,
    default=False,
    help='Enable support for an extended agent card.',
)
@click.option(
    '--dynamic-extended-card',
    is_flag=True,
    default=False,
    help='Make the extended agent card dynamic (requires --enable-extended-card).',
)
def main(dynamic_public_card, enable_extended_card, dynamic_extended_card):
    if dynamic_extended_card and not enable_extended_card:
        raise click.UsageError(
            'The --dynamic-extended-card flag requires the --enable-extended-card'
            ' flag to also be set.'
        )

    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )

    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Hello World Agent',
        description='Just a hello world agent',
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        supports_authenticated_extended_card=enable_extended_card,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    card_modifier_func = (
        create_dynamic_public_card if dynamic_public_card else None
    )
    extended_card_modifier_func = None
    static_extended_card = None

    if enable_extended_card:
        if dynamic_extended_card:
            extended_card_modifier_func = create_dynamic_extended_card
        else:
            # Create a static extended card if dynamic is not requested
            extended_skill = AgentSkill(
                id='super_hello_world',
                name='Returns a SUPER Hello World',
                description='A more enthusiastic greeting, only for authenticated users.',
                tags=['hello world', 'super', 'extended'],
                examples=['super hi', 'give me a super hello'],
            )
            static_extended_card = public_agent_card.model_copy(
                update={
                    'name': 'Hello World Agent - Extended Edition',
                    'description': 'The full-featured hello world agent for authenticated users.',
                    'version': '1.0.1',
                    'skills': [
                        skill,
                        extended_skill,
                    ],
                }
            )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
        card_modifier=card_modifier_func,
        extended_agent_card=static_extended_card,
        extended_card_modifier=extended_card_modifier_func,
    )

    uvicorn.run(server.build(), host='0.0.0.0', port=9999)


if __name__ == '__main__':
    main()
