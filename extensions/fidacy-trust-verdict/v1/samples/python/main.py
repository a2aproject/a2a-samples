"""
Fidacy Trust-Verdict Extension (A2A), Python reference sample.

Demonstrates the extension end to end:
  1. An agent assesses a payment mandate through Fidacy inside an A2A flow
     (the `A2A-Version` header negotiates A2A).
  2. Fidacy returns the verdict the A2A way, in `Task.metadata` under
     `fidacy_assessment`, carrying the signed EdDSA JWS.
  3. The client VERIFIES that JWS itself against the public JWKS (PyJWT, EdDSA-locked).
     No trust in the issuer is required.

Run:
    pip install -r requirements.txt
    export FIDACY_API_KEY=fky_test_...   # a TEST key from app.fidacy.com (sandbox, never billed)
    python main.py
"""

import os
import sys
import uuid

import requests
import jwt
from jwt import PyJWK

API = os.environ.get("FIDACY_API", "https://api.fidacy.com")
api_key = os.environ.get("FIDACY_API_KEY")
if not api_key:
    sys.exit("Set FIDACY_API_KEY (a fky_test_... key from app.fidacy.com -> API Keys, mode: test).")

# A minimal AP2 payment mandate the agent wants assessed.
mandate = {
    "vct": "mandate.payment.1",
    "transaction_id": uuid.uuid4().hex,
    "payee": {"id": "merchant_demo", "name": "Demo Store"},
    "payment_amount": {"amount": 2999, "currency": "EUR"},
    "payment_instrument": {"id": "pi_demo", "type": "card"},
}

# 1+2. Assess inside an A2A flow. The `A2A-Version` header engages A2A; the verdict
# comes back inside the `a2a` block's Task.metadata.
resp = requests.post(
    f"{API}/v1/assess",
    headers={"x-api-key": api_key, "content-type": "application/json", "A2A-Version": "1.0"},
    json={"kind": "ap2_payment", "mandate": mandate, "a2a": {"task_id": f"task_{uuid.uuid4().hex[:8]}"}},
    timeout=20,
)
resp.raise_for_status()
result = resp.json()

a2a = result.get("a2a", {})
fidacy_assessment = a2a.get("task_metadata", {}).get("fidacy_assessment", {})
jws = fidacy_assessment.get("risk_payload", {}).get("jws") or result["riskPayloadJws"]
print("A2A recommended task state:", a2a.get("recommended_task_state"))
print("Verdict rides in Task.metadata.fidacy_assessment:", bool(fidacy_assessment))

# 3. Verify the signed verdict yourself. Fetch the public JWKS and check the EdDSA
# signature; jwt.decode raises if the signature is invalid OR the alg isn't EdDSA.
jwks = requests.get(f"{API}/.well-known/jwks.json", timeout=15).json()
kid = jwt.get_unverified_header(jws)["kid"]
jwk = next(k for k in jwks["keys"] if k["kid"] == kid)
public_key = PyJWK.from_dict(jwk).key  # OKP / Ed25519
claims = jwt.decode(
    jws,
    public_key,
    algorithms=["EdDSA"],
    options={"verify_aud": False, "verify_exp": False, "verify_iat": False, "verify_nbf": False},
)

print("signature valid: True")
print("decision (verified):", claims["decision"], "· score:", claims["score"])
print("decisions match:", claims["decision"] == result["decision"])
