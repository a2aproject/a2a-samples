"""FastAPI client: AG2 codegen agent that sends code to remote reviewer via A2A."""

import asyncio

from autogen import ConversableAgent
from autogen.a2a import A2aRemoteAgent
from config import get_llm_config


config = get_llm_config()

codegen_agent = ConversableAgent(
    name='CodeGenAgent',
    description='A agent that generates code for the user',
    system_message=(
        'You are specialist in Python with huge Clean Architecture experience. '
        'Also, you are an expert in FastAPI. '
        'Please, focus on RESTful API principles while API design. '
        'Generate code in a single file. Do not use any other files. '
        'Generate just a code, no other text or comments. '
        'Terminate conversation when reviewer agent has no issues with the code.'
    ),
    is_termination_msg=lambda msg: 'No issues found.' in msg.get('content', ''),
    llm_config=config,
)


reviewer_agent = A2aRemoteAgent(
    url='http://localhost:10012',
    name='ReviewerAgent',
)


async def main() -> str:
    """Run the codegen + review loop and return the final code."""
    result = await reviewer_agent.a_initiate_chat(
        codegen_agent,
        message='Please, generate a simple FastAPI application '
        'that returns a list of users.',
    )
    return result.chat_history[-2]['content']


if __name__ == '__main__':
    code = asyncio.run(main())
    print(code)
