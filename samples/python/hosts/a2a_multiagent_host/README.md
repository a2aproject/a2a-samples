# Build Multi-Agent Systems using A2A SDK

----
> **⚠️ DISCLAIMER**: THIS DEMO IS INTENDED FOR DEMONSTRATION PURPOSES ONLY. IT IS NOT INTENDED FOR USE IN A PRODUCTION ENVIRONMENT.
>
> **⚠️ Important:** A2A is a work in progress (WIP) thus, in the near future there might be changes that are different from what demonstrated here.
----

This document describes a multi-agent set up using Agent2Agent (A2A) and a example traceability extension implementation for the hosting agents and how the extension is activated on the server and included in the response. The host can also route with a decision model instead of the LLM; see [Optional: route with Jev](#optional-route-with-jev-instead-of-the-llm).

## Architecture

The application utilizes a multi-agent architecture where a host A2A server delegates tasks to remote A2A servers (Airbnb and Weather) based on the user's query. These agents then interact using A2A proto. These A2A servers are built based ADK. We then use the CLI tool talk to the host A2A server also using A2A proto.

![architecture](assets/A2A_multi_agents.jpg)

### screenshot for CLI tool run with traceability information returned

![screenshot](assets/cli_trace_screenshot.png)

## Setup and Deployment

### Prerequisites

Before running the application locally, ensure you have the following installed:

1. **Node.js:** Required to run the Airbnb MCP server (if testing its functionality locally).
2. **uv:** The Python package management tool used in this project. Follow the installation guide: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
3. **Python 3.13** Python 3.13 is required to run a2a-sdk
4. **set up .env**

- Create a `.env` file in `samples/python/agents/airbnb_planner_multiagent/airbnb_agent` and `samples/python/agents/airbnb_planner_multiagent/weather_agent` folder with the following content:

    ```bash
    GOOGLE_API_KEY="your_api_key_here" 
    ```

- Create `.env` file in current folder with the following content:

    ```bash
    GOOGLE_GENAI_USE_VERTEXAI=TRUE
    GOOGLE_CLOUD_PROJECT="your project"
    GOOGLE_CLOUD_LOCATION=global
    AIR_AGENT_URL=http://localhost:10002
    WEA_AGENT_URL=http://localhost:10001
    ```

## 1. Run Airbnb Agent

Run the airbnb A2A agent server:

```bash
cd samples/python/agents/airbnb_planner_multiagent/airbnb_agent
uv run .
```

This will start the airbnb A2A server (port 10002).

## 2. Run Weather A2A Agent

Open a new terminal and run the weather agent server:

```bash
cd samples/python/agents/airbnb_planner_multiagent/weather_agent
uv run .
```
This will start the airbnb A2A server (port 10001).

## 3. Run Host A2A Agent

Open a new terminal and run the host agent server

```bash
cd samples/python/host/a2a_multiagent
uv run .
```
This will start the A2A Host server (port 8083).

## 4. Run the CLI Tool
```bash
cd samples/python/hosts/cli
uv run . --agent http://localhost:8083
```

Here are example questions:

- "Tell me about weather in LA, CA"  

- "Please find a room in LA, CA, June 20-25, 2025, two adults"

The response should include the traceability extension as an additional artifact. Please see the example screenshot above.
Alternatively, we can also include the traceability information as metadata in the response.

## Optional: route with Jev instead of the LLM

By default the host routes with the ADK Gemini agent in `routing_agent.py`. With
`--router jev` (or `HOST_ROUTER=jev`) it asks [TypeSafe's Jev](https://docs.typesafe.ai) which
remote agent should handle the message and forwards the message there, with no LLM in the
routing loop. Jev is a System One decision model: it does not generate text. It takes the
request and the skills advertised on the remote Agent Cards as options and returns a
probability for each, so the answer is always one of the agents or "none", with a
confidence. One HTTP call per request; the LLM path is untouched.

The decision comes back on the host's task as a `routing` artifact (agent, probabilities,
confidence, latency, tokens) next to the remote agent's own artifacts. A follow-up in the
same context, for example after the airbnb agent asks for dates, goes back to that agent
without asking Jev again. If Jev picks `none`, the task completes with "No remote agent
covers this request."; if the call fails, the task fails with the reason.

```bash
cd samples/python/hosts/a2a_multiagent_host
TYPESAFE_API_KEY=... uv run . --router jev        # remote agents running as in steps 1 and 2
cd samples/python/hosts/cli && uv run . --agent http://localhost:8083
```

| variable | default | meaning |
| --- | --- | --- |
| `HOST_ROUTER` | `llm` | `llm` or `jev`; `--router` overrides it |
| `TYPESAFE_API_KEY` | | required for `jev` |
| `SYSTEM_ONE_MODEL`, `SYSTEM_ONE_BASE_URL` | `jev-latest`, `https://api.typesafe.ai` | pin a version once you tune anything on the confidence |
| `SYSTEM_ONE_TIMEOUT` | `15` | seconds per attempt; one retry on timeout, 429 and 529 |

### Measuring it

`eval_router.py decisions` scores Jev against Gemini 2.5 Flash making the same choice with a
JSON schema whose enum is the roster, on `eval/cards` (eight synthetic cards, 13 deliberately
overlapping skills) and `eval/requests.jsonl` (52 hand-written requests, 44 covered by
exactly one skill, 8 by none; five are judgment calls and marked as such). Run of 2026-09-18
from Europe, two workers, committed as `eval/results.json`; cost uses the flags' default list
prices, $0.042 per million input tokens for Jev with free output, $0.30 in and $2.50 out per
million for Gemini 2.5 Flash with default thinking:

| metric | Jev (`jev-latest`, resolved `jev-1.13.0`) | Gemini 2.5 Flash, structured output |
| --- | --- | --- |
| accuracy, 52 requests | 98% | 98% |
| abstains on the 8 requests nothing covers | 100% | 100% |
| mean confidence when right / wrong | 0.99 / 0.91 | 1.00 / 0.90 |
| confidence >= 0.9: coverage / accuracy | 98% / 98% | 100% / 98% |
| latency p50 / p95 | 830 / 1002 ms | 1490 / 2595 ms |
| tokens in / out, whole run | 55786 / 9859 | 37834 / 11181 |
| cost per 1,000 decisions | $0.045 | $0.756 |

`eval_router.py hosts` sends the same six requests to a host started with `--router llm` and
one with `--router jev` and reports wall time and the tokens each spent on routing (Gemini's
from the traceability artifact, Jev's from the `routing` artifact). Run of the same day,
committed as `eval/hosts.json`; the airbnb agent answers `input-required` when it needs
dates or guests, which is a normal A2A state:

| request | host --router llm (Gemini) | host --router jev |
| --- | --- | --- |
| What is the weather like in LA, CA this weekend? | completed → Weather (7.3 s, 2418 tok) | completed → Weather (4.0 s, 448 tok) |
| Is it going to rain in Porto tomorrow? | completed → Weather (3.6 s, 1719 tok) | completed → Weather (3.4 s, 445 tok) |
| Find a room in LA, CA, April 15-18, 2026, two ad | completed → Airbnb (12.7 s, 2429 tok) | input-required → Airbnb (12.5 s, 460 tok) |
| I need somewhere to stay in Berlin next weekend, | completed → Airbnb (29.4 s, 10560 tok) | completed → Airbnb (13.1 s, 453 tok) |
| cheap hotel in Lisbon next weekend | completed → Airbnb (6.1 s, 2292 tok) | input-required → Airbnb (4.7 s, 442 tok) |
| Write me a limerick about a cat | completed → - (1.1 s, 706 tok) | completed → - (0.9 s, 445 tok) |
| **total** | 60.1 s, 20124 Gemini tokens (~$0.0060) | 38.6 s, 2693 Jev tokens (~$0.00011) |
| **same agent chosen** | 6 of 6 | |

Read both tables as: on this roster Jev routes as accurately as Gemini 2.5 Flash at about a
sixteenth of the cost per decision and under its latency, and the host without an LLM in the
routing loop answers faster because the Gemini routing call is gone entirely; what remains is
the remote agent's own time. Fifty-two requests show the shape, not production thresholds.
Rerun both commands on your own agents and requests.

### Tests

```bash
uv run pytest test_jev_router.py     # offline; one live test runs when TYPESAFE_API_KEY is set
```

### Caveats

- Jev reads text only, and the host forwards only the text parts of the message.
- Agent Cards remain untrusted input (see the disclaimer below). A hostile skill description
  can still lobby for itself; Jev narrows that to steering a bounded choice, since it cannot
  emit text into anything, but it does not remove it.
- Latency was measured from Europe against a US-hosted API; the vendor quotes lower numbers
  from the US West Coast.

## References

- <https://github.com/google/a2a-python>
- <https://codelabs.developers.google.com/intro-a2a-purchasing-concierge#1>
- <https://google.github.io/adk-docs/>

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description).

If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
