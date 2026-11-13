import os

from ag2 import Agent
from ag2.a2a import A2AConfig
from ag2.config import OpenAIResponsesConfig


# create A2A remote agent; the card is resolved from the remote server
reviewer_agent = Agent(
    'ReviewerAgent',
    config=A2AConfig(card_url='http://localhost:8000'),
)


codegen_agent = Agent(
    'CodeGenAgent',
    prompt=(
        'You are specialist in Python with huge Clean Architecture experience. '
        'Also, you are an expert in argparse. '
        'You should create a simple scripts based on user demands. '
        'Generate code in a single file. Do not use any other files. '
        'Do not use any external dependencies if it is possible. '
        'Use [PEP 723](https://peps.python.org/pep-0723/) to specify script dependencies if it is required. '
        'Generate just a code, no other text or comments. '
        'Always send the generated code to the reviewer agent and fix every issue it reports. '
        'Reply with the final code only when the reviewer agent has no issues with the code.'
    ),
    config=OpenAIResponsesConfig(
        model='gpt-5.6-luna',
        api_key=os.getenv('OPENAI_API_KEY'),
    ),
    # use the A2A agent as a regular sub-agent tool
    tools=[
        reviewer_agent.as_tool(
            name='review_code',
            description='Send the generated code to the remote reviewer agent and get the review back.',
        )
    ],
)


async def main() -> str | None:
    """Generate a CLI script, have it reviewed over A2A, and return the code."""
    reply = await codegen_agent.ask(
        'Please, generate a simple script, allows to transfer USD to EUR using any external API.'
    )
    return reply.body


if __name__ == '__main__':
    import asyncio

    code = asyncio.run(main())
    print(code)
