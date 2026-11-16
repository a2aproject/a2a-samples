import asyncio
import os
from uuid import uuid4

import asyncclick as click
import httpx

from google.protobuf.json_format import MessageToJson

from a2a.client import (
    A2ACardResolver,
    A2AClientError,
    ClientCallContext,
    ClientConfig,
    create_client,
)
from a2a.client.service_parameters import with_a2a_extensions
from a2a.helpers import (
    display_agent_card,
    new_raw_part,
    new_text_part,
)
from a2a.types import (
    GetTaskRequest,
    Message,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskState,
)


def proto_to_json(msg) -> str:
    return MessageToJson(msg, preserving_proto_field_name=True)


@click.command()
@click.option('--agent', default='http://localhost:8083')
@click.option(
    '--bearer-token',
    help='Bearer token for authentication.',
    envvar='A2A_CLI_BEARER_TOKEN',
)
@click.option('--session', default=0)
@click.option('--history', default=False)
@click.option('--use_push_notifications', default=False)
@click.option('--push_notification_receiver', default='http://localhost:5000')
@click.option('--header', multiple=True)
@click.option(
    '--enabled_extensions',
    default='',
    help='Comma-separated list of extension URIs to enable.',
)
async def cli(
    agent,
    bearer_token,
    session,
    history,
    use_push_notifications: bool,
    push_notification_receiver: str,
    header,
    enabled_extensions,
):
    service_params: dict[str, str] = {}
    for h in header:
        key, _, value = h.partition('=')
        service_params[key] = value

    if bearer_token:
        service_params['Authorization'] = f'Bearer {bearer_token}'

    if enabled_extensions:
        ext_list = [
            ext.strip() for ext in enabled_extensions.split(',') if ext.strip()
        ]
        if ext_list:
            with_a2a_extensions(ext_list)(service_params)

    print(f'Will use service parameters: {service_params}')

    async with httpx.AsyncClient(timeout=30) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client, agent)
        card = await card_resolver.get_agent_card()

        print('======= Agent Card ========')
        display_agent_card(card)

    config = ClientConfig(streaming=True)

    async with await create_client(card, client_config=config) as client:

        if use_push_notifications:
            import urllib.parse

            from hosts.cli.cli_v10.push_notification_listener import (
                PushNotificationListener,
            )

            notif_receiver_parsed = urllib.parse.urlparse(
                push_notification_receiver
            )
            notification_receiver_host = notif_receiver_parsed.hostname
            notification_receiver_port = notif_receiver_parsed.port

            push_notification_listener = PushNotificationListener(
                host=notification_receiver_host,
                port=notification_receiver_port,
            )
            push_notification_listener.start()

        continue_loop = True
        streaming = card.capabilities.streaming
        context_id = str(session) if session > 0 else uuid4().hex

        context = ClientCallContext(
            service_parameters=service_params if service_params else None,
        )

        while continue_loop:
            print('=========  starting a new task ======== ')
            continue_loop, context_id, task_id = await complete_task(
                client,
                streaming,
                None,
                context_id,
                context,
            )

            if history and continue_loop and task_id:
                print('========= history ======== ')
                task_response = await client.get_task(
                    GetTaskRequest(id=task_id, history_length=10),
                    context=context,
                )
                print(proto_to_json(task_response))


async def complete_task(
    client,
    streaming,
    task_id,
    context_id,
    context,
):
    prompt = await click.prompt(
        '\nWhat do you want to send to the agent? (:q or quit to exit)'
    )
    if prompt in (':q', 'quit'):
        return False, None, None

    parts = [new_text_part(prompt)]

    file_path = await click.prompt(
        'Select a file path to attach? (press enter to skip)',
        default='',
        show_default=False,
    )
    if file_path and file_path.strip():
        with open(file_path, 'rb') as f:
            file_content = f.read()
            file_name = os.path.basename(file_path)
        parts.append(new_raw_part(file_content, filename=file_name))

    msg_kwargs = {
        'role': Role.ROLE_USER,
        'parts': parts,
        'message_id': str(uuid4()),
        'context_id': context_id,
    }
    if task_id:
        msg_kwargs['task_id'] = task_id
    message = Message(**msg_kwargs)

    request = SendMessageRequest(
        message=message,
        configuration=SendMessageConfiguration(
            accepted_output_modes=['text'],
        ),
    )

    task_result = None
    response_message = None
    task_completed = False

    try:
        async for response in client.send_message(request, context=context):
            if response.HasField('task'):
                task = response.task
                task_id = task.id
                context_id = task.context_id
                if task.status.state == TaskState.TASK_STATE_COMPLETED:
                    task_completed = True
                task_result = task
            elif response.HasField('status_update'):
                event = response.status_update
                task_id = event.task_id
                context_id = event.context_id
                if event.status.state == TaskState.TASK_STATE_COMPLETED:
                    task_completed = True
            elif response.HasField('artifact_update'):
                event = response.artifact_update
                task_id = event.task_id
                context_id = event.context_id
            elif response.HasField('message'):
                response_message = response.message
                context_id = response.message.context_id

            if streaming:
                print(f'stream event => {proto_to_json(response)}')
    except A2AClientError as e:
        print(
            f'Error: {e}, context_id: {context_id}, task_id: {task_id}'
        )
        return False, context_id, task_id

    if not streaming and task_id and not task_completed:
        try:
            task_result = await client.get_task(
                GetTaskRequest(id=task_id),
                context=context,
            )
        except A2AClientError as e:
            print(
                f'Error: {e}, context_id: {context_id}, task_id: {task_id}'
            )
            return False, context_id, task_id

    if response_message:
        print(f'\n{proto_to_json(response_message)}')
        return True, context_id, task_id

    if task_result:
        print(f'\n{proto_to_json(task_result)}')
        state = task_result.status.state
        if state == TaskState.TASK_STATE_INPUT_REQUIRED:
            return await complete_task(
                client,
                streaming,
                task_id,
                context_id,
                context,
            )
        return True, context_id, task_id

    return True, context_id, task_id


if __name__ == '__main__':
    asyncio.run(cli())
