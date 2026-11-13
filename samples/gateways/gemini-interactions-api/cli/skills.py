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

"""Publish skill directories to the Vertex Skill Registry."""

from __future__ import annotations

import base64
import io
import json
import logging
import pathlib
import zipfile

from typing import TYPE_CHECKING

from cli import http


if TYPE_CHECKING:
    import argparse

    from bridge import config


logger = logging.getLogger(__name__)

_UPDATE_MASK = ('display_name', 'description', 'zipped_filesystem')


def _zip_b64(skill_dir: pathlib.Path) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob('*')):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(skill_dir).as_posix())
    return base64.b64encode(buf.getvalue()).decode('ascii')


def _description(skill_dir: pathlib.Path, fallback: str) -> str:
    """Return the first non-blank, non-heading line of SKILL.md, or `fallback` if none exists."""
    skill_doc = skill_dir / 'SKILL.md'
    if not skill_doc.is_file():
        return fallback
    for line in skill_doc.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            return stripped
    return fallback


def _srs_endpoint(region: str, override: str | None) -> str:
    if override:
        return override
    return f'https://{region}-aiplatform.googleapis.com'


def run(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    """Publishes each skill directory to the Vertex Skill Registry."""
    del registry
    root = pathlib.Path(args.dir)
    skill_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if not skill_dirs:
        raise http.CliError(f'no skill directories under {root}')

    session = http.AuthedSession(
        endpoint=_srs_endpoint(args.region, args.srs_endpoint),
        project=args.project,
        location=args.region,
    )
    published: list[str] = []
    for skill_dir in skill_dirs:
        skill_id = skill_dir.name
        body = {
            'displayName': skill_id.replace('-', ' ').title(),
            'description': _description(skill_dir, f'Skill {skill_id}'),
            'zippedFilesystem': _zip_b64(skill_dir),
        }
        if args.dry_run:
            zip_len = len(body['zippedFilesystem'])
            preview = {**body, 'zippedFilesystem': f'<{zip_len} b64 chars>'}
            print(json.dumps({skill_id: preview}, indent=2))
            continue
        logger.info('publishing skill %s', skill_id)
        result = session.upsert_and_wait(
            'skills',
            skill_id,
            body,
            update_mask=_UPDATE_MASK,
            id_param='skillId',
        )
        name = result.get('name', skill_id)
        published.append(name)
        print(name)

    if published and not args.dry_run:
        print('\nSKILL_REGISTRY_SOURCE values:')
        for name in published:
            print(f'  {name}')


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the ``publish-skills`` subcommand to *subparsers*."""
    p = subparsers.add_parser('publish-skills', help='zip and publish skills to the Skill Registry')
    p.add_argument('--dir', default='agent-template/skills')
    p.add_argument('--region', default='us-central1')
    p.add_argument(
        '--srs-endpoint',
        help='override Skill Registry host (default: regional aiplatform)',
    )
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(func=run)
