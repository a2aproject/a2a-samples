import os
import tempfile

from typing import Annotated

from autogen import ConversableAgent, LLMConfig
from autogen.a2a import A2aAgentServer
from mypy import api


# create regular AG2 agent
config = LLMConfig(
    {
        'model': 'gpt-4o-mini',
        'api_key': os.getenv('OPENAI_API_KEY'),
    }
)

reviewer_agent = ConversableAgent(
    name='ReviewerAgent',
    description='A agent that reviews the code for the user',
    system_message=(
        'You are a expert in code review pretty strict and focused on typing. '
        'Please, use mypy tool to validate the code.'
        'If mypy has no issues with the code, return "No issues found."'
    ),
    llm_config=config,
    human_input_mode='NEVER',
)


# Add mypy tool to validate the code
@reviewer_agent.register_for_llm(
    name='mypy-checker',
    description='Check the code with mypy tool',
)
def review_code_with_mypy(
    code: Annotated[str, 'Raw code content to review. Code should be formatted as single file.'],
) -> str:

    with tempfile.NamedTemporaryFile('w', suffix='.py') as tmp:
        tmp.write(code)
        stdout, stderr, exit_status = api.run([tmp.name])
    if exit_status != 0:
        return stderr
    return stdout or 'No issues found.'


# wrap agent to A2A server
server = A2aAgentServer(reviewer_agent).build()

if __name__ == '__main__':
    # run server as regular ASGI application
    import uvicorn
    uvicorn.run(server, host='0.0.0.0', port=8000)
