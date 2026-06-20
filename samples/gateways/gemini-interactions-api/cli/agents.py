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

"""Create or update a managed Vertex Interactions agent."""

from __future__ import annotations

import json
import logging
import pathlib
import string

from typing import TYPE_CHECKING, Any

from cli import http, template


if TYPE_CHECKING:
    import argparse

    from bridge import config


logger = logging.getLogger(__name__)

_DEFAULT_BASE_MODEL = 'antigravity-preview-05-2026'

_SYSTEM_INSTRUCTION = 'You operate a Linux sandbox for an enterprise user.'

_SANDBOX_NOTE = (
    'Skills are mounted under ./skills/ — read the relevant SKILL.md before '
    'acting. User-uploaded files land in /workspace/uploads/. To let the '
    'user download a file you produced, follow the [artifact-export] '
    'instructions included in each user message (signed upload URL + '
    'download link); do not use gsutil — the sandbox has no GCP credentials.'
)

_DEFAULT_TOOLS: list[dict[str, str]] = [
    {'type': 'code_execution'},
    {'type': 'filesystem'},
    {'type': 'google_search'},
    {'type': 'url_context'},
]


def _agent_id(agent_config: config.AgentConfig) -> str:
    ref = agent_config.agent
    if not ref.startswith('agents/'):
        raise http.CliError(f'{ref!r} is a base model, not a managed agent; nothing to create')
    return ref.removeprefix('agents/')


def _load_body_file(path: pathlib.Path, *, project: str, bucket: str) -> dict[str, Any]:
    """Returns the agent body from *path* with ``${PROJECT_ID}``/``${BUCKET}`` expanded.

    The ``id`` key is dropped; it is passed as the resource id, not in the body.
    """
    raw = string.Template(path.read_text()).safe_substitute(PROJECT_ID=project, BUCKET=bucket)
    body = json.loads(raw)
    body.pop('id', None)
    return body


def _build_body(agent_config: config.AgentConfig, args: argparse.Namespace) -> dict[str, Any]:
    tools: list[dict[str, Any]] = list(_DEFAULT_TOOLS)
    if args.extra_tools:
        tools.extend(json.loads(args.extra_tools))
    sources: list[dict[str, str]] = [
        {'type': 'gcs', 'source': f'gs://{args.bucket}', 'target': './agent'},
    ]
    if args.skill_registry_source:
        sources.append(
            {
                'type': 'skill_registry',
                'source': args.skill_registry_source,
                'target': './skills',
            }
        )
    env: dict[str, Any] = {
        'type': 'remote',
        'sources': sources,
        'network': {'allowlist': [{'domain': '*'}]},
    }
    if args.service_account:
        env['service_account'] = args.service_account
    instruction = agent_config.system_instruction or _SYSTEM_INSTRUCTION
    return {
        'base_agent': args.base_model,
        'description': agent_config.description,
        'system_instruction': f'{instruction}\n\n{_SANDBOX_NOTE}',
        'tools': tools,
        'base_environment': env,
    }


def run(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    """Creates or updates the managed agent selected by *args*."""
    key, agent_config = registry.resolve(args.key)
    agent_id = _agent_id(agent_config)
    logger.info('setting up managed agent %r (key=%s)', agent_id, key)

    if args.body_file:
        body = _load_body_file(
            pathlib.Path(args.body_file), project=args.project, bucket=args.bucket
        )
    else:
        if not args.skip_template_sync:
            template.sync(args.bucket, pathlib.Path(args.template_dir))
        body = _build_body(agent_config, args)

    session = http.AuthedSession(
        endpoint=args.endpoint, project=args.project, location=args.location
    )
    result = session.upsert_and_wait('agents', agent_id, body, update_mask=http.AGENT_UPDATE_MASK)
    print(json.dumps(result, indent=2))


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the ``setup-agent`` subcommand to *subparsers*."""
    p = subparsers.add_parser('setup-agent', help='create/update the managed Vertex agent')
    p.add_argument('--key', help='agents.json key (default: registry default)')
    p.add_argument('--bucket', required=True, help='GCS bucket for template')
    p.add_argument(
        '--body-file',
        help='Vertex agent JSON body to apply verbatim (with ${PROJECT_ID}/'
        '${BUCKET} substitution); bypasses the synthesised body',
    )
    p.add_argument('--service-account', help='run-as SA for the sandbox')
    p.add_argument('--skill-registry-source', help='skill_registry mount path')
    p.add_argument('--base-model', default=_DEFAULT_BASE_MODEL)
    p.add_argument('--extra-tools', help='JSON array of additional tool specs')
    p.add_argument('--template-dir', default='agent-template')
    p.add_argument('--skip-template-sync', action='store_true')
    p.set_defaults(func=run)
