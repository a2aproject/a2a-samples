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

"""Create or update a DiscoveryEngine Authorization for GE per-user OAuth.

The OAuth client secret is read from Secret Manager or stdin (never passed
on the command line) and forwarded to the DiscoveryEngine ``authorizations``
collection so Gemini Enterprise can run a server-side authorization-code
flow per end user.
"""

from __future__ import annotations

import json
import logging
import sys
import urllib.parse

from typing import TYPE_CHECKING

from cli import http


if TYPE_CHECKING:
    import argparse

    from bridge import config


logger = logging.getLogger(__name__)

_UPDATE_MASK = ('server_side_oauth2',)
_DEFAULT_SCOPES: tuple[str, ...] = (
    'openid',
    'email',
    'https://www.googleapis.com/auth/cloud-platform',
)
_AUTH_URI = 'https://accounts.google.com/o/oauth2/v2/auth'
_TOKEN_URI = 'https://oauth2.googleapis.com/token'  # noqa: S105
_DE_ENDPOINT = 'https://discoveryengine.googleapis.com'


def _read_secret(project: str, secret_id: str) -> str:
    from google.cloud import secretmanager  # noqa: PLC0415

    client = secretmanager.SecretManagerServiceClient()
    name = f'projects/{project}/secrets/{secret_id}/versions/latest'
    payload = client.access_secret_version(name=name).payload.data
    return payload.decode('utf-8').strip()


def run(args: argparse.Namespace, registry: config.AgentsRegistry) -> None:
    """Creates the DiscoveryEngine Authorization used to mint per-user tokens."""
    del registry
    if args.client_secret_stdin:
        client_secret = sys.stdin.read().strip()
    else:
        client_secret = _read_secret(args.project, args.secret_from_secret_manager)
    if not client_secret:
        raise SystemExit('client secret is empty')
    scopes = list(args.scope or _DEFAULT_SCOPES)
    # Encode spaces as %20, not +: GE re-encodes the stored authorizationUri and
    # would turn a + into a literal %2B, corrupting the space-delimited scope list
    # (which makes the OAuth consent loop). quote_via=quote gives %20.
    auth_params = urllib.parse.urlencode(
        {
            'client_id': args.oauth_client_id,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'scope': ' '.join(scopes),
        },
        quote_via=urllib.parse.quote,
    )
    body = {
        'serverSideOauth2': {
            'clientId': args.oauth_client_id,
            'clientSecret': client_secret,
            'authorizationUri': f'{_AUTH_URI}?{auth_params}',
            'tokenUri': _TOKEN_URI,
            'scopes': scopes,
        }
    }
    session = http.AuthedSession(
        endpoint=_DE_ENDPOINT,
        project=args.project,
        location='global',
        api_version='v1alpha',
    )
    result = session.upsert(
        'authorizations',
        args.name,
        body,
        update_mask=_UPDATE_MASK,
        id_param='authorizationId',
    )
    if isinstance(result.get('serverSideOauth2'), dict):
        result['serverSideOauth2'].pop('clientSecret', None)
    print(json.dumps(result, indent=2))


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the ``create-authorization`` subcommand to *subparsers*."""
    p = subparsers.add_parser(
        'create-authorization',
        help='create/update a DiscoveryEngine Authorization for GE OAuth',
    )
    p.add_argument('--name', required=True, help='authorization resource id')
    p.add_argument('--oauth-client-id', required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        '--secret-from-secret-manager',
        metavar='SECRET_ID',
        help='Secret Manager secret id holding the OAuth client secret',
    )
    src.add_argument(
        '--client-secret-stdin',
        action='store_true',
        help='read the OAuth client secret from stdin',
    )
    p.add_argument(
        '--scope',
        action='append',
        help='OAuth scope (repeatable; default: openid email cloud-platform)',
    )
    p.set_defaults(func=run)
