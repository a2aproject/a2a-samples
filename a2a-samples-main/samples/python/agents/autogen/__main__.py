import os
import logging
import click
import uvicorn
from dotenv import load_dotenv
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agents.autogen.agent_executor import CurrencyAgentExecutor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', default='localhost')
@click.option('--port', default=10000, type=int)
def main(host, port):
    if not os.getenv('OPENAI_API_KEY'):
        logger.error('OPENAI_API_KEY environment variable not set.')
        exit(1)

    # Define agent capabilities and skills
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id='convert_currency',
        name='Currency Exchange Rates Tool',
        description='Helps with exchange values between various currencies',
        tags=['currency conversion', 'currency exchange'],
        examples=['What is exchange rate between USD and GBP?'],
        inputModes=['text/plain'],
        outputModes=['text/plain'],
    )
    agent_card = AgentCard(
        name='AutoGen Currency Agent',
        description='Helps with exchange rates for currencies using A2A SDK',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        capabilities=capabilities,
        skills=[skill],
    )

    # Set up the request handler and server
    request_handler = DefaultRequestHandler(
        agent_executor=CurrencyAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logger.info(f'Starting AutoGen Currency Agent server on {host}:{port}')
    uvicorn.run(server_app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
