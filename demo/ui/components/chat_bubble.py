import html
import json

from urllib.parse import urlparse

import mesop as me

from state.state import AppState, StateMessage


@me.component
def chat_bubble(message: StateMessage, key: str) -> None:
    """Chat bubble component."""
    app_state = me.state(AppState)
    show_progress_bar = (
        message.message_id in app_state.background_tasks
        or message.message_id in app_state.message_aliases.values()
    )
    progress_text = ''
    if show_progress_bar:
        progress_text = app_state.background_tasks[message.message_id]
    if not message.content:
        print('No message content')
    for pair in message.content:
        chat_box(
            pair[0],
            pair[1],
            message.role,
            key,
            progress_bar=show_progress_bar,
            progress_text=progress_text,
        )


def chat_box(
    content: str,
    media_type: str,
    role: str,
    key: str,
    progress_bar: bool,
    progress_text: str,
) -> None:
    with me.box(
        style=me.Style(
            display='flex',
            justify_content=('space-between' if role == 'agent' else 'end'),
            min_width=500,
        ),
        key=key,
    ), me.box(
        style=me.Style(display='flex', flex_direction='column', gap=5)
    ):
        if media_type == 'image/png':
            if '/message/file' not in content:
                content = 'data:image/png;base64,' + content
            me.image(
                src=content,
                style=me.Style(
                    width='50%',
                    object_fit='contain',
                ),
            )
        elif media_type in {'application/iframe', 'iframe'}:
            render_iframe_component(content, role)
        else:
            me.markdown(
                content,
                style=me.Style(
                    font_family='Google Sans',
                    box_shadow=(
                        '0 1px 2px 0 rgba(60, 64, 67, 0.3), '
                        '0 1px 3px 1px rgba(60, 64, 67, 0.15)'
                    ),
                    padding=me.Padding(top=1, left=15, right=15, bottom=1),
                    margin=me.Margin(top=5, left=0, right=0, bottom=5),
                    background=(
                        me.theme_var('primary-container')
                        if role == 'user'
                        else me.theme_var('secondary-container')
                    ),
                    border_radius=15,
                ),
            )
    if progress_bar:
        with me.box(
            style=me.Style(
                display='flex',
                justify_content=('space-between' if role == 'user' else 'end'),
                min_width=500,
            ),
            key=key,
        ), me.box(
            style=me.Style(display='flex', flex_direction='column', gap=5)
        ), me.box(
            style=me.Style(
                font_family='Google Sans',
                box_shadow=(
                    '0 1px 2px 0 rgba(60, 64, 67, 0.3), '
                    '0 1px 3px 1px rgba(60, 64, 67, 0.15)'
                ),
                padding=me.Padding(top=1, left=15, right=15, bottom=1),
                margin=me.Margin(top=5, left=0, right=0, bottom=5),
                background=(
                    me.theme_var('primary-container')
                    if role == 'agent'
                    else me.theme_var('secondary-container')
                ),
                border_radius=15,
            ),
        ):
            if not progress_text:
                progress_text = 'Working...'
            me.text(
                progress_text,
                style=me.Style(
                    padding=me.Padding(
                        top=1, left=15, right=15, bottom=1
                    ),
                    margin=me.Margin(top=5, left=0, right=0, bottom=5),
                ),
            )
            me.progress_bar(color='accent')


def render_iframe_component(content: str, role: str) -> None:
    """Renders an iframe embedded UI component."""
    # Robust parsing of iframe data
    iframe_data = {}
    if isinstance(content, str):
        try:
            loaded_data = json.loads(content)
            if isinstance(loaded_data, dict):
                iframe_data = loaded_data
            else:
                # Valid JSON, but not a dict, treat as a simple URL
                iframe_data = {'src': content}
        except json.JSONDecodeError:
            # Not valid JSON, treat as a simple URL
            iframe_data = {'src': content}
    elif isinstance(content, dict):
        iframe_data = content
    else:
        # Fallback for unexpected content types
        iframe_data = {'src': str(content)}

    # Default iframe configuration
    src = iframe_data.get('src', '')
    width = iframe_data.get('width', '100%')
    height = iframe_data.get('height', '400px')
    title = iframe_data.get('title', 'Embedded Content')

    # Security attributes
    sandbox = iframe_data.get(
        'sandbox', 'allow-scripts allow-same-origin allow-forms'
    )
    allow = iframe_data.get(
        'allow',
        'accelerometer; autoplay; camera; encrypted-media; gyroscope; picture-in-picture',
    )

    if not src:
        me.text(
            'Error: No source URL provided for iframe',
            style=me.Style(color='red'),
        )
        return

    # Validate URL for security
    try:
        parsed_url = urlparse(src)
        if parsed_url.scheme not in ['http', 'https']:
            me.text(
                f'Error: Invalid URL scheme. Only http:// and https:// are allowed. Got: {parsed_url.scheme}',
                style=me.Style(color='red'),
            )
            return
    except Exception:
        me.text(
            'Error: Invalid URL format',
            style=me.Style(color='red'),
        )
        return

    # Create iframe container with styling
    with me.box(
        style=me.Style(
            font_family='Google Sans',
            box_shadow=(
                '0 1px 2px 0 rgba(60, 64, 67, 0.3), '
                '0 1px 3px 1px rgba(60, 64, 67, 0.15)'
            ),
            padding=me.Padding(top=10, left=15, right=15, bottom=10),
            margin=me.Margin(top=5, left=0, right=0, bottom=5),
            background=(
                me.theme_var('primary-container')
                if role == 'user'
                else me.theme_var('secondary-container')
            ),
            border_radius=15,
        )
    ):
        # Add a header if title is provided
        if title and title != 'Embedded Content':
            me.text(
                title,
                style=me.Style(
                    font_weight='500',
                    margin=me.Margin(bottom=10),
                    font_size='16px',
                ),
            )

        # Render the iframe using Mesop's HTML component with proper HTML escaping
        escaped_src = html.escape(src, quote=True)
        escaped_width = html.escape(str(width), quote=True)
        escaped_height = html.escape(str(height), quote=True)
        escaped_title = html.escape(str(title), quote=True)
        escaped_sandbox = html.escape(str(sandbox), quote=True)
        escaped_allow = html.escape(str(allow), quote=True)

        iframe_html = f'''
        <iframe
            src="{escaped_src}"
            width="{escaped_width}"
            height="{escaped_height}"
            title="{escaped_title}"
            sandbox="{escaped_sandbox}"
            allow="{escaped_allow}"
            style="border: 1px solid #ddd; border-radius: 8px; max-width: 100%;"
            loading="lazy">
            <p>Your browser does not support iframes. <a href="{escaped_src}" target="_blank">View content here</a></p>
        </iframe>
        '''

        me.html(iframe_html)
