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

"""``a2a-bridge``: admin CLI for the Vertex Interactions A2A bridge."""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys

from bridge import __main__ as bridge_main
from bridge import config

from cli import agents as agents_cmd
from cli import authz as authz_cmd
from cli import card, http, template
from cli import ge as ge_cmd
from cli import skills as skills_cmd


logger = logging.getLogger(__name__)


def _serve(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    del args, registry
    bridge_main.main()


def _print_card(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    print(json.dumps(card.build(registry, args.url, args.key), indent=2))


def _sync_template(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    del registry
    count = template.sync(args.bucket, pathlib.Path(args.template_dir))
    print(f'uploaded {count} object(s) to gs://{args.bucket}/agent-template/')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='a2a-bridge')
    parser.add_argument('--project', required=True, help='GCP project id')
    parser.add_argument('--location', default='global')
    parser.add_argument(
        '--endpoint',
        default='https://aiplatform.googleapis.com',
        help='Vertex control-plane endpoint',
    )
    parser.add_argument('--config', default='agents.json', help='path or inline JSON registry')
    parser.add_argument('-v', '--verbose', action='store_true')

    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('serve', help='run the bridge server').set_defaults(func=_serve)

    card_parser = sub.add_parser('card', help='print the A2A agent card as JSON')
    card_parser.add_argument('--url', default='/')
    card_parser.add_argument('--key')
    card_parser.set_defaults(func=_print_card)

    sync_parser = sub.add_parser('sync-template', help='upload agent-template/ to GCS')
    sync_parser.add_argument('--bucket', required=True)
    sync_parser.add_argument('--template-dir', default='agent-template')
    sync_parser.set_defaults(func=_sync_template)

    agents_cmd.add_parser(sub)
    skills_cmd.add_parser(sub)
    ge_cmd.add_parser(sub)
    authz_cmd.add_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parses arguments, loads the registry, and dispatches the subcommand."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s %(name)s: %(message)s',
    )
    registry = config.AgentsRegistry.load(
        args.config, {'PROJECT_ID': args.project, 'LOCATION': args.location}
    )
    try:
        args.func(args, registry)
    except http.CliError as err:
        print(f'error: {err}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
