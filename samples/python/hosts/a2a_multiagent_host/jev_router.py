"""Pick the remote agent for a request with TypeSafe's Jev, a System One decision model.

Jev does not generate text. It takes a ``state`` and typed questions and returns a probability
for every option you list, so the answer is always one of the remote agents' skills, or
``none``, and it comes with a confidence the host can act on. One HTTP call, no LLM involved.
"""

from __future__ import annotations

import asyncio
import re
import time

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx


if TYPE_CHECKING:
    from collections.abc import Iterable

    from a2a.types import AgentCard


NONE_KEY = 'none'
"""Option meaning "no listed skill covers the request"."""

MAX_OPTIONS = 255
"""Options one Choice question can hold, ``none`` included."""

ATTEMPTS = 2
"""One retry on 429, 529 and timeouts."""

_SLUG_RE = re.compile(r'[^a-z0-9]+')


def _slug(text: str) -> str:
    return _SLUG_RE.sub('-', text.lower()).strip('-')


@dataclass(frozen=True)
class Candidate:
    """One option Jev can pick: a skill of a remote agent, described by its card."""

    key: str
    agent_name: str
    skill_id: str
    description: str


def candidates_from_cards(cards: Iterable[AgentCard]) -> list[Candidate]:
    """Flatten every skill on every card into an option; a card without skills is one option."""
    candidates: list[Candidate] = []
    for card in cards:
        if not card.skills:
            candidates.append(
                Candidate(
                    key=f'{_slug(card.name)}__agent',
                    agent_name=card.name,
                    skill_id='',
                    description=f'{card.name}: {card.description}',
                )
            )
            continue
        for skill in card.skills:
            parts = [f'{skill.name} (agent: {card.name}): {skill.description}']
            if skill.tags:
                parts.append('Tags: ' + ', '.join(skill.tags))
            if skill.examples:
                parts.append('Examples: ' + '; '.join(skill.examples[:3]))
            candidates.append(
                Candidate(
                    key=f'{_slug(card.name)}__{_slug(skill.id)}',
                    agent_name=card.name,
                    skill_id=skill.id,
                    description='. '.join(parts),
                )
            )
    return candidates


@dataclass
class Route:
    """Jev's answer for one request."""

    agent_name: str | None
    """Remote agent to send the request to, or ``None`` when Jev picked ``none``."""

    skill_id: str | None
    probabilities: dict[str, float]
    """Probability per option key, ``none`` included; sums to 1."""

    confidence: float
    """How peaked the distribution is on the chosen option, 0 to 1."""

    model: str
    latency_ms: float
    usage: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """JSON-serialisable form, attached to the host's response as a ``routing`` artifact."""
        return {
            'agent_name': self.agent_name,
            'skill_id': self.skill_id,
            'confidence': round(self.confidence, 4),
            'probabilities': {k: round(v, 4) for k, v in self.probabilities.items()},
            'model': self.model,
            'latency_ms': round(self.latency_ms, 1),
            'usage': self.usage,
        }


class JevRouter:
    """Ask Jev which remote agent should handle a request.

    One request carries one Choice question whose options are every skill on the remote
    cards plus ``none``. Retries once on 429, 529 and timeouts; any other failure propagates
    so the caller can fail the task with the reason.
    """

    def __init__(
        self,
        api_key: str,
        model: str = 'jev-latest',
        base_url: str = 'https://api.typesafe.ai',
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._url = base_url.rstrip('/') + '/v1/systemone'
        self._timeout = timeout
        self._client = client

    async def route(self, text: str, cards: Iterable[AgentCard]) -> Route:
        """Return the remote agent Jev picks for ``text``."""
        candidates = candidates_from_cards(cards)
        if not candidates:
            raise ValueError('no remote agents to route to')
        if len(candidates) >= MAX_OPTIONS:
            raise ValueError(
                f'{len(candidates)} skills do not fit the {MAX_OPTIONS - 1} options of one question'
            )
        criteria = {c.key: c.description for c in candidates}
        criteria[NONE_KEY] = 'No listed skill covers the request'
        body = {
            'model': self.model,
            'state': {'request': text},
            'questions': {
                'route': {
                    'type': 'choice',
                    'instructions': (
                        'Which listed skill should handle `request`? '
                        'Pick `none` if no skill clearly covers it.'
                    ),
                    'criteria': criteria,
                }
            },
        }
        started = time.perf_counter()
        data = await self._post(body)
        answer = data['answers']['route']
        by_key = {c.key: c for c in candidates}
        chosen = by_key.get(answer['choice'])
        return Route(
            agent_name=chosen.agent_name if chosen else None,
            skill_id=chosen.skill_id if chosen else None,
            probabilities={k: float(v) for k, v in answer['probabilities'].items()},
            confidence=float(answer.get('confidence', 0.0)),
            model=str(data.get('model', self.model)),
            latency_ms=(time.perf_counter() - started) * 1000,
            usage={k: v for k, v in (data.get('usage') or {}).items() if isinstance(v, int)},
        )

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {'Authorization': f'Bearer {self._api_key}'}
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            for attempt in range(1, ATTEMPTS + 1):
                try:
                    response = await client.post(self._url, json=body, headers=headers)
                except httpx.TimeoutException:
                    if attempt == ATTEMPTS:
                        raise
                    continue
                if response.status_code in (429, 529) and attempt < ATTEMPTS:
                    await asyncio.sleep(0.5)
                    continue
                response.raise_for_status()
                return response.json()
            raise RuntimeError('unreachable')
        finally:
            if client is not self._client:
                await client.aclose()
