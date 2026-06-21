"""Fidacy Trust-Verdict Extension (A2A): Python reference sample.

Assesses a payment mandate through Fidacy inside an A2A flow, then verifies the
signed EdDSA verdict against the public JWKS. No trust in the issuer is required.

Run:
    pip install -r requirements.txt
    export FIDACY_API_KEY=fky_test_...
    python main.py
"""

from __future__ import annotations

import os
import sys
import uuid

import jwt
import requests

from jwt import PyJWK


def main() -> None:
    """Assess a mandate over A2A and verify the signed verdict."""
    api = os.environ.get('FIDACY_API', 'https://api.fidacy.com')
    api_key = os.environ.get('FIDACY_API_KEY')
    if not api_key:
        sys.exit('Set FIDACY_API_KEY (a fky_test_... key from app.fidacy.com).')

    mandate = {
        'vct': 'mandate.payment.1',
        'transaction_id': uuid.uuid4().hex,
        'payee': {'id': 'merchant_demo', 'name': 'Demo Store'},
        'payment_amount': {'amount': 2999, 'currency': 'EUR'},
        'payment_instrument': {'id': 'pi_demo', 'type': 'card'},
    }

    resp = requests.post(
        f'{api}/v1/assess',
        headers={'x-api-key': api_key, 'content-type': 'application/json', 'A2A-Version': '1.0'},
        json={
            'kind': 'ap2_payment',
            'mandate': mandate,
            'a2a': {'task_id': f'task_{uuid.uuid4().hex[:8]}'},
        },
        timeout=20,
    )
    resp.raise_for_status()
    result = resp.json()

    a2a = result.get('a2a', {})
    fidacy_assessment = a2a.get('task_metadata', {}).get('fidacy_assessment', {})
    jws = fidacy_assessment.get('risk_payload', {}).get('jws') or result.get('riskPayloadJws')
    if not jws:
        sys.exit('JWS not found in the assessment response.')
    print('A2A recommended task state:', a2a.get('recommended_task_state'))
    print('Verdict rides in Task.metadata.fidacy_assessment:', bool(fidacy_assessment))

    jwks = requests.get(f'{api}/.well-known/jwks.json', timeout=15).json()
    kid = jwt.get_unverified_header(jws)['kid']
    jwk = next((k for k in jwks['keys'] if k['kid'] == kid), None)
    if not jwk:
        sys.exit(f"Key id '{kid}' not found in the JWKS.")
    public_key = PyJWK.from_dict(jwk).key
    claims = jwt.decode(
        jws,
        public_key,
        algorithms=['EdDSA'],
        options={
            'verify_aud': False,
            'verify_exp': False,
            'verify_iat': False,
            'verify_nbf': False,
        },
    )

    print('signature valid: True')
    print('decision (verified):', claims.get('decision'), 'score:', claims.get('score'))
    print('decisions match:', claims.get('decision') == result.get('decision'))


if __name__ == '__main__':
    main()
