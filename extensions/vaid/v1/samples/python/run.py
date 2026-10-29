# Copyright 2026 Solara Associates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Minimal VAID A2A extension sample.

An issuer mints a VAID for an agent, the agent carries it on an A2A
``Message``, and a receiver verifies it with ``vaid_a2a.verify_a2a_message``.
Two requests are checked: one inside the VAID's scope (accepted) and one
outside it (refused).
"""

from __future__ import annotations

import base64

from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from vaid_a2a import METADATA_VAID_KEY, verify_a2a_message
from vaid_mint.document import (
    build_unsigned_vaid_document,
    canonical_vaid_signing_bytes,
    compute_lineage_hash,
    prefix_entry,
)
from vaid_mint.issuer_identity import kernel_key_thumbprint
from vaid_mint.revocation import InMemoryRevocationList


TRUST_DOMAIN = 'vaid.example'


def b64url(raw: bytes) -> str:
    """Base64url-encode ``raw`` with no padding, as the extension's AgentCard shape expects."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def mint_leaf_vaid(agent_id: str, scope: list[str], kernel_key: Ed25519PrivateKey) -> dict:
    """Mint a root (no parent) VAID for ``agent_id``, scoped to ``scope``.

    A real issuer would use ``vaid_mint.mint.MintService``; this builds the
    document directly so the sample has no dependency beyond ``vaid_mint``
    and ``vaid_a2a``.
    """
    public_key = kernel_key.public_key().public_bytes_raw()
    unsigned = build_unsigned_vaid_document(
        vaid_id=agent_id,
        agent_id=agent_id,
        agent_class='sample-agent',
        version='1.0.0',
        tenant_id='acme',
        issued_at='2026-01-01T00:00:00Z',
        expires_at='2099-01-01T00:00:00Z',
        public_key_der=list(range(32)),
        parent_vaid=None,
        scope_boundary=[prefix_entry(s) for s in scope],
        lineage_hash=compute_lineage_hash(None, agent_id),
        capability_set=['read'],
        trust_domain=TRUST_DOMAIN,
        kernel_key_thumbprint=kernel_key_thumbprint(public_key),
    )
    signature = kernel_key.sign(canonical_vaid_signing_bytes(unsigned))
    return {**unsigned, 'kernel_signature': list(signature)}


def send(vaid: dict) -> dict:
    """An agent attaching its VAID to an outgoing A2A ``Message``."""
    return {'metadata': {METADATA_VAID_KEY: vaid}}


def receive(message: dict, trust_config: dict, requested_action: str) -> None:
    """A receiver verifying the VAID on an incoming A2A ``Message``."""
    result = verify_a2a_message(
        message,
        trust_config=trust_config,
        revocation=InMemoryRevocationList.assume_nothing_revoked(),
        requested_action=requested_action,
        now=datetime.now(timezone.utc),
    )
    verdict = 'ACCEPTED' if result.allowed else 'REFUSED'
    print(
        f'  requested_action={requested_action!r} -> {verdict} ({result.code.value}: {result.reason})'
    )


def main() -> None:
    """Mint a VAID, attach it to a message, and verify two requested actions."""
    kernel_key = Ed25519PrivateKey.generate()
    trust_config = {
        'trustedIssuers': [
            {
                'trustDomain': TRUST_DOMAIN,
                'kernelPublicKey': b64url(kernel_key.public_key().public_bytes_raw()),
            }
        ]
    }

    vaid = mint_leaf_vaid('agent:orders-worker', ['data.orders.read'], kernel_key)
    message = send(vaid)

    print('VAID A2A extension: minimal accept/refuse demo')
    print(f'issuer trust domain: {TRUST_DOMAIN!r}, agent scope: {vaid["scope_boundary"]!r}')
    receive(message, trust_config, 'data.orders.read')
    receive(message, trust_config, 'data.orders.write')


if __name__ == '__main__':
    main()
