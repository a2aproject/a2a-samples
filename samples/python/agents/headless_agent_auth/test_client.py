import asyncio
import os

from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import asyncclick as click
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    GetTaskRequest,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
    TaskArtifactUpdateEvent,
    TaskQueryParams,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)
from auth0.authentication.get_token import GetToken
from dotenv import load_dotenv


load_dotenv()


class AgentAuth(httpx.Auth):
    """Custom httpx's authentication class to inject access token required by agent."""

    _access_token: str | None = None

    def __init__(self, agent_card: AgentCard) -> None:
        """Initialize the agent auth."""
        self.agent_card = agent_card

    def auth_flow(self, request: httpx.Request):
        """Handle the authentication flow."""
        # 1. Get the schemes map
        schemes_obj = getattr(self.agent_card, 'security_schemes', {})
        # Handle Pydantic RootModel wrapper if it exists
        security_schemes = (
            schemes_obj.root if hasattr(schemes_obj, 'root') else schemes_obj
        )

        # Convert to dict if it's a Pydantic model so we can iterate keys
        if not isinstance(security_schemes, dict):
            security_schemes = (
                security_schemes.model_dump()
                if hasattr(security_schemes, 'model_dump')
                else dict(security_schemes)
            )

        # 2. Find the OAuth2 scheme (using the key we know exists)
        auth_scheme = security_schemes.get('oauth2_m2m')

        # 3. Extract the Token URL
        # Turn the object into a dict so we can see EVERYTHING, including aliases
        scheme_dict = (
            auth_scheme
            if isinstance(auth_scheme, dict)
            else auth_scheme.model_dump(by_alias=True)
        )

        # Look for 'flows' or 'flows' (aliased)
        flows = scheme_dict.get('flows')

        token_url = None
        if flows:
            # The A2A spec uses 'clientCredentials' in JSON
            # We check every possible naming convention
            cc_flow = (
                flows.get('clientCredentials')
                or flows.get('client_credentials')
                or flows.get('client-credentials')
            )

            if cc_flow:
                token_url = cc_flow.get('tokenUrl') or cc_flow.get('token_url')

        if not self._access_token:
            print(f'\nFetching agent access token from {token_url}...')
            get_token = GetToken(
                domain=urlparse(str(token_url)).hostname,
                client_id=os.getenv('A2A_CLIENT_AUTH0_CLIENT_ID'),
                client_secret=os.getenv('A2A_CLIENT_AUTH0_CLIENT_SECRET'),
            )
            AgentAuth._access_token = get_token.client_credentials(
                os.getenv('HR_AGENT_AUTH0_AUDIENCE')
            )['access_token']
            print('Done.\n')

        request.headers['Authorization'] = f'Bearer {self._access_token}'
        yield request


@click.command()
@click.option('--agent', default='http://localhost:10050')
@click.option('--context_id')
@click.option('--history', default=False, is_flag=True)
@click.option('--debug', default=False, is_flag=True)
async def cli(
    agent: str, context_id: str | None, history: bool, debug: bool
) -> None:
    """Run the A2A test client."""
    # 1. Define a robust timeout (e.g., 60 seconds)
    # We set 'read' to None to allow the stream to stay open indefinitely
    # as long as the server is still sending chunks.
    timeout = httpx.Timeout(60.0, read=None)

    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        agent_card = await (
            A2ACardResolver(
                httpx_client=httpx_client,
                base_url=agent,
            )
        ).get_agent_card()

        print('======= Agent Card ========')
        print(agent_card.model_dump_json(exclude_none=True, indent=2))

        httpx_client.auth = AgentAuth(agent_card)

        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=agent_card,
        )

        if not context_id:
            context_id = uuid4().hex

        continue_loop = True
        streaming = agent_card.capabilities.streaming

        while continue_loop:
            task_id = None
            print('=========  Starting a New Task ======== ')
            continue_loop, task_id = await complete_task(
                client,
                streaming,
                task_id,
                context_id,
                debug,
            )

            if history and continue_loop:
                print('========= History ======== ')
                get_task_response = await client.get_task(
                    GetTaskRequest(
                        id=str(uuid4()),
                        params=TaskQueryParams(id=task_id, history_length=10),
                    )
                )
                print(
                    get_task_response.root.model_dump_json(
                        include={'result': {'history': True}}
                    )
                )


def create_send_params(
    text: str, task_id: str | None = None, context_id: str | None = None
) -> MessageSendParams:
    """Helper function to create the payload for sending a task."""
    send_params: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [{'type': 'text', 'text': text}],
            'messageId': uuid4().hex,
        },
        'configuration': {
            'acceptedOutputModes': ['text'],
        },
    }

    if task_id:
        send_params['message']['taskId'] = task_id

    if context_id:
        send_params['message']['contextId'] = context_id

    return MessageSendParams(**send_params)


def extract_output_from_result(result: Any) -> str:
    """Extract text output from various A2A result types."""
    output = ''
    if isinstance(result, TaskStatusUpdateEvent) and result.status.message:
        # This catches "Looking up...", "Processing...", and the final error
        output = next(
            (
                p.root.text
                for p in result.status.message.parts
                if isinstance(p.root, TextPart)
            ),
            '',
        )
    elif isinstance(result, Message):
        output = next(
            (p.root.text for p in result.parts if isinstance(p.root, TextPart)),
            '',
        )
    elif isinstance(result, TaskArtifactUpdateEvent):
        # Handle artifacts (though we prefer status messages for the main reply)
        if hasattr(result.artifact, 'text'):
            output = result.artifact.text
    elif hasattr(result, 'status') and result.status.message:
        # Handle Task objects if they appear in the stream
        output = next(
            (
                p.root.text
                for p in result.status.message.parts
                if isinstance(p.root, TextPart)
            ),
            '',
        )
    return output


async def complete_task(
    client: A2AClient,
    streaming: bool,
    task_id: str | None,
    context_id: str,
    debug: bool = False,
) -> tuple[bool, str | None]:
    """Send a message to the agent and wait for completion."""
    prompt = click.prompt(
        '\nWhat do you want to send to the agent? (:q or quit to exit)'
    )

    if prompt in {':q', 'quit'}:
        return False, task_id

    send_params = create_send_params(
        text=prompt,
        task_id=task_id,
        context_id=context_id,
    )

    task = None
    if streaming:
        stream_response = client.send_message_streaming(
            SendStreamingMessageRequest(id=str(uuid4()), params=send_params)
        )
        async for chunk in stream_response:
            result = chunk.root.result

            # 1. CAPTURE THE TASK ID (Crucial fix)
            # The logs show the ID is in result.id OR result.task_id
            task_id = (
                getattr(result, 'id', None)
                or getattr(result, 'task_id', None)
                or task_id
            )

            # 2. EXTRACT TEXT FROM STATUS UPDATES
            output = extract_output_from_result(result)

            if output:
                # This will stop the "empty result chunk" messages and show you the Agent's thoughts
                print(f'Agent: {output}')

        # 3. FINAL VALIDATION: Only poll if we actually got an ID
        if task_id:
            get_task_response = await client.get_task(
                GetTaskRequest(
                    id=str(uuid4()), params=TaskQueryParams(id=task_id)
                )
            )
            task = get_task_response.root.result

            # Print the final result if it's available in the task status
            if task and task.status.message:
                final_output = next(
                    (
                        p.root.text
                        for p in task.status.message.parts
                        if isinstance(p.root, TextPart)
                    ),
                    '',
                )
                if final_output:
                    print(f'\nFinal Result: {final_output}')
        else:
            print('\nError: Agent stream ended without providing a Task ID.')
            return False, task_id
    else:
        # non-streaming path
        send_message_response = await client.send_message(
            SendMessageRequest(id=str(uuid4()), params=send_params)
        )
        task = send_message_response.root.result
        task_id = task.id
        # Simple print for non-streaming
        print(
            f'\nAgent: {next((p.root.text for p in task.status.message.parts if isinstance(p.root, TextPart)), "Done.")}'
        )

    # Handle recursion for "input_required"
    if task and task.status.state == TaskState.input_required:
        return await complete_task(
            client, streaming, task_id, context_id, debug
        )

    # task is complete
    return True, task_id


if __name__ == '__main__':
    asyncio.run(cli())


if __name__ == '__main__':
    asyncio.run(cli())
