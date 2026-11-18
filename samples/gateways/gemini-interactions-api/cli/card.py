# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Build A2A AgentCard JSON from the agents registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from bridge import config


_PROTOCOL_VERSION = '0.3.0'
_CARD_VERSION = '0.1.0'

_ADK_A2A_EXTENSION = 'https://google.github.io/adk-docs/a2a/a2a-extension/'

_GOOGLE_OIDC_DISCOVERY = 'https://accounts.google.com/.well-known/openid-configuration'
_CLOUD_PLATFORM_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'

_SECURITY_SCHEMES: dict[str, Any] = {
    'google_oidc': {
        'type': 'openIdConnect',
        'openIdConnectUrl': _GOOGLE_OIDC_DISCOVERY,
    },
    'google_oauth2': {
        'type': 'oauth2',
        'flows': {
            'authorizationCode': {
                'authorizationUrl': ('https://accounts.google.com/o/oauth2/v2/auth'),
                'tokenUrl': 'https://oauth2.googleapis.com/token',
                'scopes': {
                    _CLOUD_PLATFORM_SCOPE: 'Google Cloud Platform',
                },
            }
        },
    },
}

_SECURITY: list[dict[str, list[str]]] = [
    {'google_oidc': []},
    {'google_oauth2': [_CLOUD_PLATFORM_SCOPE]},
]


def _describe(agents: dict[str, config.AgentConfig]) -> str:
    lines = []
    for agent_config in agents.values():
        tags = f' ({", ".join(agent_config.tags)})' if agent_config.tags else ''
        lines.append(f'- {agent_config.display_name} — {agent_config.description}{tags}')
    return '\n'.join(lines)


def _skill(key: str, agent_config: config.AgentConfig) -> dict[str, Any]:
    return {
        'id': key,
        'name': agent_config.display_name,
        'description': agent_config.description,
        'tags': list(agent_config.tags),
    }


def build(
    registry: config.AgentsRegistry,
    url: str,
    key: str | None = None,
) -> dict[str, Any]:
    """Returns an A2A AgentCard dict.

    When *key* is given the card is scoped to that agent (single skill, URL
    suffixed with ``/{key}``); otherwise it advertises every registered agent.
    """
    url = url.rstrip('/')
    if key:
        selected_key, selected = registry.resolve(key)
        url = f'{url}/{selected_key}'
        skills = [_skill(selected_key, selected)]
        description = selected.description
    else:
        selected = registry.default_agent
        skills = [_skill(key, agent_config) for key, agent_config in registry.agents.items()]
        description = _describe(registry.agents)
    return {
        'protocolVersion': _PROTOCOL_VERSION,
        'name': selected.display_name,
        'description': description,
        'url': url,
        'version': _CARD_VERSION,
        'capabilities': {
            'streaming': True,
            'extensions': [{'uri': _ADK_A2A_EXTENSION, 'required': False}],
        },
        'defaultInputModes': ['text/plain'],
        'defaultOutputModes': ['text/plain'],
        'securitySchemes': _SECURITY_SCHEMES,
        'security': _SECURITY,
        'skills': skills,
    }
