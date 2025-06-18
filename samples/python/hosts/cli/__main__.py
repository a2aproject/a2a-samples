import asyncio
import json
import os
import shutil
import subprocess
import urllib

from uuid import uuid4

import asyncclick as click
import httpx

from a2a.client import (
    A2ACardResolver,
    A2AClient,
    AuthInterceptor,
    ClientCallContext,
    InMemoryContextCredentialStore,
)
from a2a.types import (
    FilePart,
    FileWithBytes,
    GetTaskRequest,
    HTTPAuthSecurityScheme,
    JSONRPCErrorResponse,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    OAuth2SecurityScheme,
    OpenIdConnectSecurityScheme,
    Part,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskQueryParams,
    TaskState,
    TextPart,
)
from common.utils.push_notification_auth import PushNotificationReceiverAuth


def pretty_print_event(event):
    """Formats and prints server events for better readability."""
    if not event:
        return

    print('=' * 50)
    event_kind = getattr(event, 'kind', type(event).__name__).upper()

    task_id = getattr(event, 'taskId', getattr(event, 'id', 'N/A'))
    print(f'EVENT TYPE: {event_kind} | Task ID: {task_id}')

    print('-' * 50)

    if hasattr(event, 'status') and event.status:
        print(f'  Status: {event.status.state}')
        if event.status.message and event.status.message.parts:
            text_parts = [
                p.root.text
                for p in event.status.message.parts
                if isinstance(p.root, TextPart)
            ]
            if text_parts:
                print(f'  Message: {" ".join(text_parts)}')

    artifacts_to_print = []
    if isinstance(event, Task) and event.artifacts:
        artifacts_to_print = event.artifacts
    elif hasattr(event, 'artifact') and event.artifact:
        artifacts_to_print = [event.artifact]

    if artifacts_to_print:
        print('  Artifacts:')
        for artifact in artifacts_to_print:
            for part in artifact.parts:
                if isinstance(part.root, TextPart):
                    print(f'    - {part.root.text}')
                elif isinstance(part.root, FilePart):
                    file_info = part.root.file
                    file_name = getattr(file_info, 'name', 'Unnamed File')
                    print(f'    - [File Artifact: {file_name}]')

    if isinstance(event, Message):
        print(f'  Role: {event.role}')
        if event.parts:
            text_parts = [
                p.root.text for p in event.parts if isinstance(p.root, TextPart)
            ]
            if text_parts:
                print(f'  Content: {" ".join(text_parts)}')

    print('=' * 50, '\n')


@click.command()
@click.option('--agent', default='http://localhost:10000')
@click.option(
    '--session', default=0, help='A numeric ID to reuse a client-side session.'
)
@click.option('--history', default=False)
@click.option('--use_push_notifications', default=False)
@click.option('--push_notification_receiver', default='http://localhost:5000')
@click.option(
    '--gcloud-auth',
    is_flag=True,
    default=False,
    help='Automatically use gcloud to get an ID token for authentication.',
)
async def cli(
    agent,
    session,
    history,
    use_push_notifications: bool,
    push_notification_receiver: str,
    gcloud_auth: bool,
):
    credential_service = InMemoryContextCredentialStore()
    auth_interceptor = AuthInterceptor(credential_service)

    async with httpx.AsyncClient(timeout=30) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client, agent)
        card = await card_resolver.get_agent_card()

        print('======= Agent Card ========')
        print(json.dumps(card.model_dump(exclude_none=True), indent=2))

        notif_receiver_parsed = urllib.parse.urlparse(
            push_notification_receiver
        )
        notification_receiver_host = notif_receiver_parsed.hostname
        notification_receiver_port = notif_receiver_parsed.port

        if use_push_notifications:
            from hosts.cli.push_notification_listener import (
                PushNotificationListener,
            )

            notification_receiver_auth = PushNotificationReceiverAuth()
            await notification_receiver_auth.load_jwks(
                f'{agent}/.well-known/jwks.json'
            )

            push_notification_listener = PushNotificationListener(
                host=notification_receiver_host,
                port=notification_receiver_port,
                notification_receiver_auth=notification_receiver_auth,
            )
            push_notification_listener.start()

        client = A2AClient(
            httpx_client, agent_card=card, interceptors=[auth_interceptor]
        )

        streaming = card.capabilities.streaming

        # This ID is for the client-side session to manage credentials. It does not go to the server.
        session_id = str(session) if session > 0 else uuid4().hex
        client_context = ClientCallContext(state={'sessionId': session_id})

        token_to_set = None
        bearer_scheme_name = None

        if card.security and card.securitySchemes:
            for scheme_name, scheme_def_union in card.securitySchemes.items():
                if not scheme_def_union:
                    continue
                scheme_def = scheme_def_union.root
                is_bearer_scheme = isinstance(
                    scheme_def,
                    (
                        HTTPAuthSecurityScheme,
                        OAuth2SecurityScheme,
                        OpenIdConnectSecurityScheme,
                    ),
                )
                if is_bearer_scheme:
                    bearer_scheme_name = scheme_name
                    break

        if gcloud_auth and bearer_scheme_name:
            print(
                'GCloud auth requested and agent supports bearer token authentication.'
            )
            if not shutil.which('gcloud'):
                print(
                    "WARNING: --gcloud-auth was passed, but 'gcloud' command not found in PATH."
                )
            else:
                try:
                    proc = subprocess.run(
                        ['gcloud', 'auth', 'print-identity-token'],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    token_to_set = proc.stdout.strip()
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f'WARNING: Failed to get gcloud identity token: {e}')

        if token_to_set and bearer_scheme_name:
            print(f'DEBUG: Using token: {token_to_set[:15]}...')
            await credential_service.set_credential(
                session_id, bearer_scheme_name, token_to_set
            )
            print(
                f'Associated bearer token with security scheme: {bearer_scheme_name}'
            )

        # These variables track the server-side conversation state.
        server_context_id = None
        task_id = None
        continue_loop = True

        while continue_loop:
            print('=========  Starting a new turn ======== ')
            continue_loop, server_context_id, task_id = await completeTask(
                client=client,
                streaming=streaming,
                use_push_notifications=use_push_notifications,
                notification_receiver_host=notification_receiver_host,
                notification_receiver_port=notification_receiver_port,
                task_id=task_id,
                client_context=client_context,
                server_context_id=server_context_id,
            )

            if history and continue_loop and task_id:
                print('========= History for Task ======== ')
                task_response = await client.get_task(
                    GetTaskRequest(
                        id=str(uuid4()), params=TaskQueryParams(id=task_id)
                    ),
                    context=client_context,
                )

                pretty_print_event(task_response.root.result)


async def completeTask(
    client: A2AClient,
    streaming: bool,
    use_push_notifications: bool,
    notification_receiver_host: str,
    notification_receiver_port: int,
    task_id: str | None,
    client_context: ClientCallContext,
    server_context_id: str | None,
) -> tuple[bool, str | None, str | None]:
    prompt = click.prompt(
        '\nWhat do you want to send to the agent? (:q or quit to exit)'
    )
    if prompt.lower() in [':q', 'quit']:
        return False, server_context_id, task_id

    current_server_context_id = server_context_id

    message = Message(
        role='user',
        parts=[TextPart(text=prompt)],
        messageId=str(uuid4()),
        taskId=task_id,
        contextId=current_server_context_id,
    )

    file_path = click.prompt(
        'Select a file path to attach? (press enter to skip)',
        default='',
        show_default=False,
    )
    if file_path and file_path.strip() != '':
        with open(file_path, 'rb') as f:
            file_content = f.read()
            file_name = os.path.basename(file_path)
        message.parts.append(
            Part(
                root=FilePart(
                    file=FileWithBytes(name=file_name, bytes=file_content)
                )
            )
        )

    payload = MessageSendParams(
        id=str(uuid4()),
        message=message,
        configuration=MessageSendConfiguration(
            acceptedOutputModes=['text'],
        ),
    )

    if use_push_notifications:
        payload['pushNotification'] = {
            'url': f'http://{notification_receiver_host}:{notification_receiver_port}/notify',
            'authentication': {'schemes': ['bearer']},
        }

    task_result = None
    final_message = None
    # Keep track of the latest context ID received from the server.
    latest_server_context_id = current_server_context_id

    if streaming:
        response_stream = client.send_message_streaming(
            SendStreamingMessageRequest(id=str(uuid4()), params=payload),
            context=client_context,
        )
        async for result in response_stream:
            if isinstance(result.root, JSONRPCErrorResponse):
                print('Error: ', result.root.error)
                return False, latest_server_context_id, task_id

            event = result.root.result
            latest_server_context_id = getattr(
                event, 'contextId', latest_server_context_id
            )
            task_id = getattr(event, 'taskId', getattr(event, 'id', task_id))

            if isinstance(event, Message):
                final_message = event
            pretty_print_event(event)

        if task_id:
            get_task_response = await client.get_task(
                GetTaskRequest(
                    id=str(uuid4()), params=TaskQueryParams(id=task_id)
                ),
                context=client_context,
            )
            task_result = get_task_response.root.result
    else:
        try:
            event = await client.send_message(
                SendMessageRequest(id=str(uuid4()), params=payload),
                context=client_context,
            )
            event = event.root.result
            latest_server_context_id = getattr(
                event, 'contextId', latest_server_context_id
            )

            if isinstance(event, Task):
                task_id = event.id
                task_result = event
            elif isinstance(event, Message):
                final_message = event
            pretty_print_event(event)
        except Exception as e:
            print(f'Failed to complete the call: {e}')

    while True:
        if final_message:
            return True, latest_server_context_id, task_id
        if not task_result:
            return True, latest_server_context_id, task_id

        state = TaskState(task_result.status.state)

        if state == TaskState.input_required:
            return True, latest_server_context_id, task_id
        if state == TaskState.auth_required:
            print(
                '\nAuthorization is required. Please use the URL from the task status to authenticate.'
            )
            print('Polling for task completion...')
            updated_task = task_result
            while (
                TaskState(updated_task.status.state) == TaskState.auth_required
            ):
                await asyncio.sleep(3)
                print(f'Polling task {task_id} for status update...')
                get_task_response = await client.get_task(
                    GetTaskRequest(
                        id=str(uuid4()), params=TaskQueryParams(id=task_id)
                    ),
                    context=client_context,
                )
                updated_task = get_task_response.root.result
                pretty_print_event(updated_task)

            task_result = updated_task
            final_message = None
            continue

        return True, latest_server_context_id, task_id


if __name__ == '__main__':
    asyncio.run(cli())
