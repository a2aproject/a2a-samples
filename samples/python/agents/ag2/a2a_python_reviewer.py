import os
import tempfile

from typing import Annotated

import uvicorn

from mypy import api
from pydantic import Field

from ag2 import Agent, tool
from ag2.a2a import A2AServer, build_card
from ag2.config import OpenAIResponsesConfig


HOST = '127.0.0.1'
PORT = 8000
# URL the agent card advertises; clients resolve the transport endpoint from it
URL = f'http://localhost:{PORT}'


# Add mypy tool to validate the code
@tool(
    name='mypy_checker',
    description='Check the code with mypy tool',
)
def review_code_with_mypy(
    code: Annotated[
        str,
        Field(description='Raw code content to review. Code should be formatted as single file.'),
    ],
) -> str:
    """Type-check a code snippet with mypy and return its report."""
    with tempfile.NamedTemporaryFile('w', suffix='.py') as tmp:
        tmp.write(code)
        tmp.flush()
        stdout, stderr, exit_status = api.run([tmp.name])
    if exit_status != 0 and stderr:
        return stderr
    return stdout or 'No issues found.'


# create regular AG2 agent
reviewer_agent = Agent(
    'ReviewerAgent',
    prompt=(
        'You are an expert in code review pretty strict and focused on typing. '
        'Please, use mypy tool to validate the code.'
        'If mypy has no issues with the code, return "No issues found."'
    ),
    config=OpenAIResponsesConfig(
        model='gpt-5.6-luna',
        api_key=os.getenv('OPENAI_API_KEY'),
    ),
    tools=[review_code_with_mypy],
)


# wrap agent to A2A server and expose it over JSON-RPC
server = A2AServer(reviewer_agent)
card = build_card(
    reviewer_agent,
    url=URL,
    description='An agent that reviews the code for the user',
)
app = server.build_jsonrpc(url=URL, card=card)

if __name__ == '__main__':
    # run server as regular ASGI application
    uvicorn.run(app, host=HOST, port=PORT)
