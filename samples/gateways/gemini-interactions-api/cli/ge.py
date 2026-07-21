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

"""Register the bridge as an A2A agent in a Gemini Enterprise app."""

from __future__ import annotations

import json
import logging

from typing import TYPE_CHECKING, Any

from cli import card, http


if TYPE_CHECKING:
    import argparse

    from bridge import config


logger = logging.getLogger(__name__)

_UPDATE_MASK = (
    'display_name',
    'description',
    'icon',
    'sharing_config',
    'custom_placeholder_text',
    'starter_prompts',
    'a2a_agent_definition',
    'authorization_config',
)

_DEFAULT_STARTERS = [
    'run uname -a and show me the output',
    'write and run a python script that prints the first 20 primes',
]


def _endpoint(location: str) -> str:
    if location == 'global':
        return 'https://discoveryengine.googleapis.com'
    return f'https://{location}-discoveryengine.googleapis.com'


def _body(registry: config.AgentsRegistry, args: argparse.Namespace) -> dict[str, Any]:
    a2a_card = card.build(registry, args.url, args.key)
    _, agent_config = registry.resolve(args.key)
    starters = agent_config.starter_prompts or _DEFAULT_STARTERS
    body: dict[str, Any] = {
        'displayName': a2a_card['name'],
        'description': a2a_card['description'],
        'sharingConfig': {'scope': 'ALL_USERS'},
        'customPlaceholderText': f'Ask {a2a_card["name"]}…',
        'starterPrompts': [{'text': prompt} for prompt in starters],
        'a2aAgentDefinition': {'jsonAgentCard': json.dumps(a2a_card)},
    }
    if args.icon_url:
        body['icon'] = {'uri': args.icon_url}
    return body


def _resolve_authorization(session: http.AuthedSession, authorization: str) -> str:
    if authorization.startswith('projects/'):
        return authorization
    return session.json('GET', f'authorizations/{authorization}')['name']


def run(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    """Registers (or updates) the agent in a Gemini Enterprise app."""
    session = http.AuthedSession(
        endpoint=_endpoint(args.location),
        project=args.project,
        location=args.location,
        api_version='v1alpha',
    )
    body = _body(registry, args)
    if args.authorization:
        body['authorizationConfig'] = {
            'agentAuthorization': _resolve_authorization(session, args.authorization)
        }
    collection = (
        f'collections/default_collection/engines/{args.app}/assistants/default_assistant/agents'
    )
    agent_id = args.id or args.key or registry.default
    result = session.upsert_and_wait(
        collection,
        agent_id,
        body,
        update_mask=_UPDATE_MASK,
        id_param='agentId',
    )
    print(json.dumps(result, indent=2))


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the ``register-ge`` subcommand to *subparsers*."""
    p = subparsers.add_parser('register-ge', help='register the bridge in a Gemini Enterprise app')
    p.add_argument('--app', required=True, help='GE engine/app id')
    p.add_argument('--url', required=True, help='public Cloud Run URL')
    p.add_argument('--key', help='agents.json key for a single-agent card')
    p.add_argument('--id', help='GE agent resource id (default: --key or registry default)')
    p.add_argument('--icon-url', help='icon URI shown in GE')
    p.add_argument(
        '--authorization',
        help='DiscoveryEngine Authorization id to attach for per-user OAuth',
    )
    p.set_defaults(func=run)
