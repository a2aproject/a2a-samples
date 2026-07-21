# Fidacy Trust-Verdict (A2A), Python sample

Runs the extension end to end: assess a payment mandate through Fidacy over A2A, then **verify the
signed verdict yourself** against the public JWKS (no trust in the issuer).

```bash
pip install -r requirements.txt
export FIDACY_API_KEY=fky_test_...   # a TEST key from app.fidacy.com -> API Keys (mode: test, sandbox)
python main.py
```

Expected output ends with `signature valid: True` and `decisions match: True`. The verdict rode in
`Task.metadata.fidacy_assessment.risk_payload.jws`; verification used only the public JWKS.
