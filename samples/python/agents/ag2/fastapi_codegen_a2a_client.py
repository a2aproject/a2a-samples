import os

from autogen import ConversableAgent, LLMConfig
from autogen.a2a import A2aRemoteAgent


config = LLMConfig(
    {
        'model': 'gpt-4o-mini',
        'api_key': os.getenv('OPENAI_API_KEY'),
    }
)

codegen_agent = ConversableAgent(
    name='CodeGenAgent',
    description='A agent that generates code for the user',
    system_message=(
        'You are specialist in Python with huge Clear Architecture experience. '
        'Also, you are an expert in FastAPI. '
        'Please, focus on REST-full API principles while API design. '
        'Generate code in a single file. Do not use any other files. '
        'Generate just a code, no other text or comments. '
        'Terminate conversation when reviewer agent has no issues with the code.'
    ),
    is_termination_msg=lambda msg: 'No issues found.' in msg.get('content', ''),
    llm_config=config,
)


# create A2A remote agent
reviewer_agent = A2aRemoteAgent(
    url='http://localhost:8000',
    name='ReviewerAgent',
)


async def main() -> str:
    # use A2A agent as regular one
    result = await reviewer_agent.a_initiate_chat(
        codegen_agent,
        message='Please, generate a simple FastAPI application that returns a list of users.',
    )
    return result.chat_history[-2]['content']


if __name__ == '__main__':
    import asyncio

    code = asyncio.run(main())
    print(code)
