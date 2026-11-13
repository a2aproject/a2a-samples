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
        'Also, you are an expert in FastAPI. '
        'Please, focus on RESTful API principles while API design. '
        'Generate code in a single file. Do not use any other files. '
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
    """Generate a FastAPI application, have it reviewed over A2A, and return the code."""
    reply = await codegen_agent.ask(
        'Please, generate a simple FastAPI application that returns a list of users.'
    )
    return reply.body


if __name__ == '__main__':
    import asyncio

    code = asyncio.run(main())
    print(code)
