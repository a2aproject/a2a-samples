import uuid

from a2a.types import (
    FilePart,
    FileWithUri,
    Message,
    Part,
    Role,
)


test_image = Message(
    role=Role.agent,
    message_id=str(uuid.uuid4()),
    context_id='',
    parts=[
        Part(
            root=FilePart(
                file=FileWithUri(
                    name='6a6bab940d1340ab9ca8d1e6d9bd2b23',
                    mime_type='image/png',
                    uri='https://a2a-protocol.org/latest/assets/a2a-banner.png',
                ),
                metadata=None,
            )
        )
    ],
)


def make_test_image(context_id: str) -> Message:
    test_image.context_id = context_id
    return test_image
