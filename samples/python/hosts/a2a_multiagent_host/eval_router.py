"""Measure Jev as a router: decision accuracy, latency and cost, and the host end to end.

Two commands. ``decisions`` scores Jev against a Gemini structured-output baseline on the
labelled requests in ``eval/`` (eight synthetic cards, 52 requests)::

    uv run eval_router.py decisions --out eval/results.json

``hosts`` sends the same requests to a host running with ``--router llm`` and one running
with ``--router jev`` and reports wall time, tokens and cost per request; Gemini tokens come
from the traceability extension the LLM host implements, Jev tokens from the ``routing``
artifact the Jev host returns::

    uv run eval_router.py hosts --llm-host http://localhost:8083 --jev-host http://localhost:8084
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
import uuid

from pathlib import Path
from typing import Any

import click
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    DataPart,
    MessageSendParams,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TextPart,
)
from dotenv import load_dotenv
from google import genai
from jev_router import NONE_KEY, JevRouter, candidates_from_cards
from traceability_ext import TRACEABILITY_EXTENSION_URI


load_dotenv()

HERE = Path(__file__).resolve().parent
GATE = 0.9
"""Confidence at or above which a decision counts as gated-in."""
GEMINI_PROMPT = (
    'You route user requests to the agent skill best able to handle them.\n'
    'Skills (key: description):\n{roster}\n- {none}: no listed skill covers the request\n\n'
    'Request: {query}\n\n'
    'Reply with JSON holding the chosen skill key and your confidence from 0 to 1.'
)
DEFAULT_QUERIES = (
    'What is the weather like in LA, CA this weekend?',
    'Is it going to rain in Porto tomorrow?',
    'Find a room in LA, CA, April 15-18, 2026, two adults',
    'I need somewhere to stay in Berlin next weekend, budget 120 a night',
    'cheap hotel in Lisbon next weekend',
    'Write me a limerick about a cat',
)


# --- decisions --------------------------------------------------------------------------


async def gemini_decide(
    client: genai.Client, model: str, text: str, cards: list[AgentCard]
) -> dict[str, Any]:
    """The same decision from Gemini with a JSON schema whose enum is the roster."""
    candidates = candidates_from_cards(cards)
    keys = [c.key for c in candidates] + [NONE_KEY]
    roster = '\n'.join(f'- {c.key}: {c.description}' for c in candidates)
    schema = {
        'type': 'object',
        'properties': {
            'choice': {'type': 'string', 'enum': keys},
            'confidence': {'type': 'number'},
        },
        'required': ['choice', 'confidence'],
    }
    started = time.perf_counter()
    response = await client.aio.models.generate_content(
        model=model,
        contents=GEMINI_PROMPT.format(roster=roster, none=NONE_KEY, query=text),
        config={'response_mime_type': 'application/json', 'response_schema': schema},
    )
    data = json.loads(response.text or '{}')
    meta = response.usage_metadata
    choice = data.get('choice', NONE_KEY)
    return {
        'chosen': None if choice == NONE_KEY else choice,
        'confidence': max(0.0, min(1.0, float(data.get('confidence', 0.0)))),
        'latency_ms': (time.perf_counter() - started) * 1000,
        'usage': {
            'input_tokens': int(getattr(meta, 'prompt_token_count', 0) or 0),
            'output_tokens': int(getattr(meta, 'candidates_token_count', 0) or 0)
            + int(getattr(meta, 'thoughts_token_count', 0) or 0),
        },
    }


async def jev_decide(router: JevRouter, text: str, cards: list[AgentCard]) -> dict[str, Any]:
    """Jev's decision, keyed the same way as Gemini's."""
    route = await router.route(text, cards)
    chosen = None
    if route.agent_name is not None:
        chosen = next(
            c.key
            for c in candidates_from_cards(cards)
            if c.agent_name == route.agent_name and c.skill_id == route.skill_id
        )
    return {
        'chosen': chosen,
        'confidence': route.confidence,
        'latency_ms': route.latency_ms,
        'usage': route.usage,
    }


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(p * len(ordered)) - 1))] if ordered else 0.0


def summarize(rows: list[dict[str, Any]], price_in: float, price_out: float) -> dict[str, Any]:
    """Aggregate one model's rows."""
    ok = [r for r in rows if r.get('error') is None]
    n = len(rows)
    none_rows = [r for r in ok if r['expected'] is None]
    gated = [r for r in ok if r['confidence'] >= GATE]
    tokens_in = sum(r['usage'].get('input_tokens', 0) for r in ok)
    tokens_out = sum(r['usage'].get('output_tokens', 0) for r in ok)
    cost = (tokens_in * price_in + tokens_out * price_out) / 1e6
    right = [r['confidence'] for r in ok if r['correct']]
    wrong = [r['confidence'] for r in ok if not r['correct']]
    return {
        'n': n,
        'errors': n - len(ok),
        'accuracy': sum(r['correct'] for r in ok) / n if n else 0.0,
        'none_recall': (sum(r['chosen'] is None for r in none_rows) / len(none_rows))
        if none_rows
        else None,
        'confidence_right': statistics.fmean(right) if right else None,
        'confidence_wrong': statistics.fmean(wrong) if wrong else None,
        'gated_coverage': len(gated) / n if n else 0.0,
        'gated_accuracy': (sum(r['correct'] for r in gated) / len(gated)) if gated else None,
        'p50_ms': percentile([r['latency_ms'] for r in ok], 0.5),
        'p95_ms': percentile([r['latency_ms'] for r in ok], 0.95),
        'tokens_in': tokens_in,
        'tokens_out': tokens_out,
        'cost_per_1k_usd': cost / n * 1000 if n else 0.0,
    }


def confidence_cell(s: dict[str, Any]) -> str:
    """Mean confidence when right / when wrong."""
    right = f'{s["confidence_right"] or 0:.2f}'
    wrong = '-' if s['confidence_wrong'] is None else f'{s["confidence_wrong"]:.2f}'
    return f'{right} / {wrong}'


def pct(x: float | None) -> str:
    """Percent or dash."""
    return '-' if x is None else f'{x * 100:.0f}%'


def decisions_table(summaries: dict[str, dict[str, Any]]) -> str:
    """Markdown table, models as columns."""
    names = list(summaries)
    rows = [
        ('requests', lambda s: str(s['n'])),
        ('accuracy', lambda s: pct(s['accuracy'])),
        ('abstains on requests nothing covers', lambda s: pct(s['none_recall'])),
        ('mean confidence when right / wrong', confidence_cell),
        (
            'confidence >= 0.9: coverage / accuracy',
            lambda s: f'{pct(s["gated_coverage"])} / {pct(s["gated_accuracy"])}',
        ),
        ('latency p50 / p95', lambda s: f'{s["p50_ms"]:.0f} / {s["p95_ms"]:.0f} ms'),
        ('tokens in / out, whole run', lambda s: f'{s["tokens_in"]} / {s["tokens_out"]}'),
        ('cost per 1,000 decisions', lambda s: f'${s["cost_per_1k_usd"]:.3f}'),
        ('errors', lambda s: str(s['errors'])),
    ]
    out = ['| metric | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    out.extend(
        f'| {label} | ' + ' | '.join(f(summaries[n]) for n in names) + ' |' for label, f in rows
    )
    return '\n'.join(out)


@click.group()
def cli() -> None:
    """Evaluate Jev as the host's router."""


@cli.command()
@click.option(
    '--cards', 'cards_dir', type=click.Path(path_type=Path), default=HERE / 'eval' / 'cards'
)
@click.option(
    '--requests',
    'requests_path',
    type=click.Path(path_type=Path),
    default=HERE / 'eval' / 'requests.jsonl',
)
@click.option('--workers', default=2, show_default=True)
@click.option('--gemini-model', default='gemini-2.5-flash', show_default=True)
@click.option(
    '--jev-input-price', default=0.042, show_default=True, help='USD per million input tokens'
)
@click.option(
    '--gemini-input-price', default=0.30, show_default=True, help='USD per million input tokens'
)
@click.option(
    '--gemini-output-price', default=2.50, show_default=True, help='USD per million output tokens'
)
@click.option('--out', 'out_path', type=click.Path(path_type=Path), default=None)
def decisions(  # noqa: PLR0913 - one parameter per flag
    *,
    cards_dir: Path,
    requests_path: Path,
    workers: int,
    gemini_model: str,
    jev_input_price: float,
    gemini_input_price: float,
    gemini_output_price: float,
    out_path: Path | None,
) -> None:
    """Jev versus Gemini structured output on the labelled requests."""
    cards = [
        AgentCard.model_validate(json.loads(p.read_text()))
        for p in sorted(cards_dir.glob('*.json'))
    ]
    requests = [json.loads(line) for line in requests_path.read_text().splitlines() if line.strip()]
    api_key = os.getenv('TYPESAFE_API_KEY')
    if not api_key:
        raise click.UsageError('TYPESAFE_API_KEY is required')
    router = JevRouter(
        api_key=api_key,
        model=os.getenv('SYSTEM_ONE_MODEL', 'jev-latest'),
        timeout=float(os.getenv('SYSTEM_ONE_TIMEOUT', '30')),
    )
    gemini = (
        genai.Client() if (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')) else None
    )
    semaphore = asyncio.Semaphore(workers)

    async def score(name: str, decide: Any) -> list[dict[str, Any]]:
        async def one(request: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                try:
                    result = await decide(request['text'])
                except Exception as e:  # noqa: BLE001 - keep the run going, count the error
                    return {
                        **request,
                        'chosen': None,
                        'correct': False,
                        'confidence': 0.0,
                        'latency_ms': 0.0,
                        'usage': {},
                        'error': f'{type(e).__name__}: {e}',
                    }
            return {
                **request,
                **result,
                'correct': result['chosen'] == request['expected'],
                'error': None,
            }

        click.echo(f'running {name} on {len(requests)} requests ...', err=True)
        return await asyncio.gather(*(one(r) for r in requests))

    async def main() -> dict[str, Any]:
        results: dict[str, Any] = {}
        results['jev'] = await score('jev', lambda text: jev_decide(router, text, cards))
        if gemini is not None:
            client = gemini
            results[gemini_model] = await score(
                gemini_model, lambda text: gemini_decide(client, gemini_model, text, cards)
            )
        prices = {
            'jev': (jev_input_price, 0.0),
            gemini_model: (gemini_input_price, gemini_output_price),
        }
        summaries = {name: summarize(rows, *prices[name]) for name, rows in results.items()}
        click.echo(decisions_table(summaries))
        return {'summaries': summaries, 'rows': results}

    payload = asyncio.run(main())
    if out_path:
        out_path.write_text(json.dumps(payload, indent=2) + '\n')
        click.echo(f'wrote {out_path}', err=True)


# --- hosts ------------------------------------------------------------------------------


async def ask_host(client: httpx.AsyncClient, card: AgentCard, text: str) -> dict[str, Any]:
    """One request to a host; wall time, final state, agent used, tokens spent on routing."""
    request = SendMessageRequest(
        id=uuid.uuid4().hex,
        params=MessageSendParams.model_validate(
            {
                'message': {
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': text}],
                    'messageId': uuid.uuid4().hex,
                }
            }
        ),
    )
    headers = {
        'X-A2A-Extensions': TRACEABILITY_EXTENSION_URI,
        'A2A-Extensions': TRACEABILITY_EXTENSION_URI,
    }
    started = time.perf_counter()
    try:
        response = await A2AClient(client, card).send_message(
            request, http_kwargs={'headers': headers}
        )
    except Exception as e:  # noqa: BLE001
        return {
            'state': f'error: {type(e).__name__}',
            'ms': (time.perf_counter() - started) * 1000,
            'agent': '-',
            'tokens': 0,
        }
    ms = (time.perf_counter() - started) * 1000
    if not isinstance(response.root, SendMessageSuccessResponse):
        return {
            'state': f'error: {response.root.error.message}',
            'ms': ms,
            'agent': '-',
            'tokens': 0,
        }
    task = response.root.result
    if not isinstance(task, Task):
        return {'state': 'message', 'ms': ms, 'agent': '-', 'tokens': 0}
    agent, tokens, answer = '-', 0, ''
    for artifact in task.artifacts or []:
        for part in artifact.parts:
            if isinstance(part.root, DataPart) and 'route' in part.root.data:  # the jev host
                route = part.root.data['route']
                agent = route.get('agent_name') or '-'
                tokens += int(route.get('usage', {}).get('input_tokens', 0))
                continue
            if not isinstance(part.root, TextPart):
                continue
            try:
                trace = json.loads(part.root.text)
            except ValueError:
                answer = part.root.text
                continue
            if isinstance(trace, dict) and 'steps' in trace:  # the llm host's traceability artifact
                for step in trace['steps']:
                    tokens += int(step.get('total_tokens') or 0)
                    if str(step.get('call_type', '')).upper() == 'AGENT':
                        agent = step.get('name', agent)
            else:
                answer = part.root.text
    return {
        'state': task.status.state.value,
        'ms': ms,
        'agent': agent,
        'tokens': tokens,
        'answer': answer[:120],
    }


@cli.command()
@click.option('--llm-host', default='http://localhost:8083', show_default=True)
@click.option('--jev-host', default='http://localhost:8084', show_default=True)
@click.option(
    '--query', 'queries', multiple=True, help='Repeatable; defaults to six built-in requests.'
)
@click.option(
    '--gemini-price',
    default=0.30,
    show_default=True,
    help='USD per million tokens, applied to the trace total',
)
@click.option('--jev-price', default=0.042, show_default=True, help='USD per million input tokens')
@click.option('--out', 'out_path', type=click.Path(path_type=Path), default=None)
def hosts(  # noqa: PLR0913 - one parameter per flag
    *,
    llm_host: str,
    jev_host: str,
    queries: tuple[str, ...],
    gemini_price: float,
    jev_price: float,
    out_path: Path | None,
) -> None:
    """The LLM-routed host versus the Jev-routed host, end to end."""

    async def main() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=180) as client:
            llm_card = await A2ACardResolver(client, llm_host).get_agent_card()
            jev_card = await A2ACardResolver(client, jev_host).get_agent_card()
            rows: list[dict[str, Any]] = []
            for text in queries or DEFAULT_QUERIES:
                click.echo(f'· {text}', err=True)
                rows.append(
                    {
                        'query': text,
                        'llm': await ask_host(client, llm_card, text),
                        'jev': await ask_host(client, jev_card, text),
                    }
                )
            lines = [
                '| request | host --router llm (Gemini) | host --router jev |',
                '|---|---|---|',
            ]
            for r in rows:
                cells = [
                    f'{r[k]["state"]} → {r[k]["agent"].replace(" Agent", "")} ({r[k]["ms"] / 1000:.1f} s, {r[k]["tokens"]} tok)'
                    for k in ('llm', 'jev')
                ]
                lines.append(f'| {r["query"][:48]} | {cells[0]} | {cells[1]} |')
            t_llm = sum(r['llm']['ms'] for r in rows) / 1000
            t_jev = sum(r['jev']['ms'] for r in rows) / 1000
            k_llm = sum(r['llm']['tokens'] for r in rows)
            k_jev = sum(r['jev']['tokens'] for r in rows)
            agree = sum(r['llm']['agent'] == r['jev']['agent'] for r in rows)
            lines.append(
                f'| **total** | {t_llm:.1f} s, {k_llm} Gemini tokens (~${k_llm * gemini_price / 1e6:.4f}) | {t_jev:.1f} s, {k_jev} Jev tokens (~${k_jev * jev_price / 1e6:.5f}) |'
            )
            lines.append(f'| **same agent chosen** | {agree} of {len(rows)} | |')
            click.echo('\n'.join(lines))
            return {'rows': rows}

    payload = asyncio.run(main())
    if out_path:
        out_path.write_text(json.dumps(payload, indent=2) + '\n')


if __name__ == '__main__':
    cli()
