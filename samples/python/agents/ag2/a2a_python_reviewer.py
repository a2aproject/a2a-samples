import os
import tempfile

from typing import Annotated

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
    description='An agent that reviews the code for the user',
    system_message=(
        'You are an expert in code review pretty strict and focused on typing. '
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
    code: Annotated[
        str,
        'Raw code content to review. Code should be formatted as single file.',
    ],
) -> str:
    # Windows fix: close file before mypy reads it
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        stdout, stderr, exit_status = api.run([tmp_path, '--ignore-missing-imports'])
    finally:
        os.unlink(tmp_path)
    if exit_status != 0:
        return stdout or stderr
    return stdout or 'No issues found.'


# wrap agent to A2A server
server = A2aAgentServer(reviewer_agent).build()

if __name__ == '__main__':
    # run server as regular ASGI application
    import uvicorn

    uvicorn.run(server, host='0.0.0.0', port=8000)
