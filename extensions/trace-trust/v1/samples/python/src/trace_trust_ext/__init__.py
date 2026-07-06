import logging
import os

from collections.abc import Callable
from typing import Any, Optional

import httpx

from pydantic import BaseModel, Field


# --- Extension Definition ---
TRACE_TRUST_URI = 'https://github.com/a2aproject/a2a-samples/tree/main/extensions/trace-trust'
TRACE_API_URL = os.getenv('TRACE_API_URL', 'https://traceapi-xxf56.ondigitalocean.app/v1/score')


# Fallback type if a2a-python is not installed (for isolated testing)
class BaseA2AMessage(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


try:
    from a2a.types import A2AMessage
except ImportError:
    A2AMessage = BaseA2AMessage


class TraceTrustExtension:
    """
    Middleware utility class for enforcing TRACE reputation scores on incoming A2A messages.
    """

    def __init__(self, api_key: str, min_score: float = 0.35, fail_closed: bool = True):
        self.api_key = api_key
        self.min_score = min_score
        self.fail_closed = fail_closed
        self.client = httpx.Client(timeout=5.0)

    def _get_trace_score(self, provider_id: str) -> float | None:
        """Calls the real TRACE API to fetch the global reputation score."""
        try:
            response = self.client.post(
                TRACE_API_URL,
                json={
                    'provider_id': provider_id,
                    'job': {'category': 'a2a-interaction', 'weight': 1.0},
                },
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
            )
            response.raise_for_status()
            data = response.json()
            # TRACE API returns data -> reputation -> score
            return data.get('data', {}).get('reputation', {}).get('score', 0.0)
        except Exception as e:
            logging.exception('TRACE API request failed')
            if self.fail_closed:
                raise PermissionError(
                    f'TRACE API unreachable and fail_closed is True. Denying access. Error: {e}'
                ) from e
            return None

    def server_middleware(
        self, next_handler: Callable[[A2AMessage], Any], message: A2AMessage, caller_id: str
    ):
        """
        Intercepts incoming A2A messages and enforces TRACE trust policies.
        """
        logging.info('[TRACE Middleware] Verifying caller: %s', caller_id)

        score = self._get_trace_score(caller_id)

        if score is None:
            logging.warning(
                '[TRACE Middleware] Could not retrieve score. Fail-closed is False, permitting request.'
            )
        elif score < self.min_score:
            logging.error(
                '[TRACE Middleware] REJECTED: Caller %s has insufficient reputation (%s < %s)',
                caller_id,
                score,
                self.min_score,
            )
            raise PermissionError(
                f'Access Denied: Sender reputation ({score}) is below the required threshold ({self.min_score}).'
            )
        else:
            logging.info(
                '[TRACE Middleware] ACCEPTED: Caller %s is trusted (Score: %s)', caller_id, score
            )

        return next_handler(message)
