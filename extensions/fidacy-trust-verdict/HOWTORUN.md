# How to run

The reference sample is Python and lives in [`v1/samples/python`](./v1/samples/python).

```bash
cd v1/samples/python
pip install -r requirements.txt
export FIDACY_API_KEY=fky_test_...   # a TEST key from app.fidacy.com -> API Keys (mode: test)
python main.py
```

It assesses a payment mandate through Fidacy with the `A2A-Version: 1.0` header, reads the verdict
from `Task.metadata.fidacy_assessment`, and verifies the signed EdDSA JWS against the public JWKS.
Expected: `signature valid: True`.
