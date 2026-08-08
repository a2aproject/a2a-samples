# GSAR Verification — trusting what a peer agent tells you

An A2A host that checks a remote peer's final answer against the peer's
own real, structured task output — using [GSAR](https://tulipagents.ai/concepts/gsar/)
(typed claim/evidence grounding — [arXiv:2604.23366](https://arxiv.org/abs/2604.23366)) from the
[tulip-agents](https://tulipagents.ai) SDK, a real dependency of this sample only.

## The gap this demonstrates

A2A gives every completed `Task` a final `Message` (the peer's natural-
language answer) alongside its `Artifacts` (the peer's actual structured
output). Nothing in the protocol checks that the two agree — a peer can
call the right skill, get the right data back in its own artifact, and
still misreport it in the message it sends you. From the host's side,
without checking, there's no way to tell a peer that got it right from one
that got the data and said something else anyway.

This sample runs a real reservation-lookup agent two ways — honestly, and
with a fabricated detail in its own summary of its own real lookup — and
shows a host correctly telling them apart by scoring the final message
against the artifact as evidence.

## Layout

```text
gsar_verification/
├── agent_executor.py   # the remote peer -- honest or fabricating summaries
├── __main__.py          # serves it over real A2A (same wiring as helloworld)
├── host_verify.py       # the new piece: GSAR-scores the peer's answer
└── requirements.txt
```

## Try it

```bash
pip install -r requirements.txt

# Terminal 1 -- an honest peer
python __main__.py 9999

# Terminal 2 -- verify it
export OPENAI_API_KEY=sk-...
python host_verify.py http://127.0.0.1:9999 ZFA04Y
```

```text
GSAR verdict: grounding_score=1.00 decision=resolved
```

Now the same peer, told to summarize sloppily instead:

```bash
REMOTE_AGENT_MODE=hallucinating python __main__.py 9999
python host_verify.py http://127.0.0.1:9999 ZFA04Y
```

```text
GSAR verdict: grounding_score=0.00 decision=resolved
  contradicted: ['Reservation ZFA04Y for Mei Chen — business class, SFO to JFK, 3 checked bags included at no charge.']
```

Both runs are the exact same real lookup, the exact same real artifact —
only the peer's own summary differs. `host_verify.py` never sees which
mode is active; it only sees the message and the artifact, same as any
real host would.

## Scope

This is a host deciding whether to trust what a peer told it — a different,
complementary problem from access control or task authorization. It
doesn't gate, block, or deny anything; it scores. `tulip-agents` is a
dependency of this sample only, declared in its own `requirements.txt` —
nothing else in this repository imports it.
