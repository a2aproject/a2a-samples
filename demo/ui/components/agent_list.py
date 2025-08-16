import mesop as me
import pandas as pd

from a2a.types import AgentCard
from state.agent_state import AgentState


@me.component
def agents_list(
    agents: list[AgentCard],
):
    """Agents list component."""
    df_data: dict[str, list[str | bool | None]] = {
        'Address': [],
        'Name': [],
        'Description': [],
        'Organization': [],
        'Input Modes': [],
        'Output Modes': [],
        'Extensions': [],
        'Streaming': [],
    }
    for agent_info in agents:
        df_data['Address'].append(agent_info.url)
        df_data['Name'].append(agent_info.name)
        df_data['Description'].append(agent_info.description)
        df_data['Organization'].append(
            agent_info.provider.organization if agent_info.provider else ''
        )
        df_data['Input Modes'].append(', '.join(agent_info.default_input_modes))
        df_data['Output Modes'].append(
            ', '.join(agent_info.default_output_modes)
        )
        df_data['Streaming'].append(agent_info.capabilities.streaming)
        df_data['Extensions'].append(
            ', '.join([ext.uri for ext in agent_info.capabilities.extensions])
            if agent_info.capabilities.extensions
            else ''
        )
    df = pd.DataFrame(
        pd.DataFrame(df_data),
        columns=[
            'Address',
            'Name',
            'Description',
            'Organization',
            'Input Modes',
            'Output Modes',
            'Extensions',
            'Streaming',
        ],
    )
    with me.box(
        style=me.Style(
            display='flex',
            justify_content='space-between',
            flex_direction='column',
        )
    ):
        me.table(
            df,
            header=me.TableHeader(sticky=True),
            columns={
                'Address': me.TableColumn(sticky=True),
                'Name': me.TableColumn(sticky=True),
                'Description': me.TableColumn(sticky=True),
            },
        )
        with me.content_button(
            type='raised',
            on_click=add_agent,
            key='new_agent',
            style=me.Style(
                display='flex',
                flex_direction='row',
                gap=5,
                align_items='center',
                margin=me.Margin(top=10),
            ),
        ):
            me.icon(icon='upload')


def add_agent(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Import agent button handler."""
    state = me.state(AgentState)
    state.agent_dialog_open = True
