"""
Basic Usage Example: Rate Limiting Extension

This example demonstrates how to implement rate limiting in an A2A agent executor
with the rate limiting extension for communicating usage signals to clients.

Key Points:
- Rate limiting is ALWAYS enforced (protects agent resources)
- Extension is OPTIONALLY activated by clients (provides usage visibility)
- Clients activate by sending X-A2A-Extensions header
"""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message
from ratelimiter_ext import RateLimitingExtension, TokenBucketLimiter


class MyAgentExecutor(AgentExecutor):
    """Example agent executor with rate limiting."""

    def __init__(self):
        # Rate limiter for ENFORCEMENT (always active)
        # capacity_multiplier=2.0 allows burst of 2x the rate limit
        self.rate_limiter = TokenBucketLimiter(capacity_multiplier=2.0)

        # Extension for COMMUNICATION (activated by client)
        self.rate_limit_ext = RateLimitingExtension()

    def _get_client_key(self, context: RequestContext) -> str:
        """Extract client identifier for rate limiting.

        In production, use OAuth token, API key, etc.
        IP address is used here for simplicity but not recommended for production.
        """
        return f"ip:{getattr(context, 'remote_addr', 'unknown')}"

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute agent with rate limiting."""

        # Step 1: ALWAYS enforce rate limits (regardless of extension activation)
        client_key = self._get_client_key(context)
        usage = self.rate_limiter.check_limit(
            key=client_key,
            limit=10,  # 10 requests
            window=60,  # per minute
        )

        # Step 2: If rate limited, return error message
        if not usage.allowed:
            error_msg = (
                f"Rate limit exceeded. {usage.remaining} requests remaining. "
                f"Retry after {usage.retry_after:.1f} seconds."
            )
            message = new_agent_text_message(error_msg)

            # Step 3: Add usage signals IF client requested them
            if self.rate_limit_ext.is_activated(context):
                self.rate_limit_ext.add_usage_signals(message, usage)

            await event_queue.enqueue_event(message)
            return

        # Step 4: Process request normally (rate limit not exceeded)
        # In a real agent, this would invoke your actual agent logic
        result = "Hello! Request processed successfully."
        message = new_agent_text_message(result)

        # Step 5: Add usage signals IF client requested them (success case)
        if self.rate_limit_ext.is_activated(context):
            self.rate_limit_ext.add_usage_signals(message, usage)

        await event_queue.enqueue_event(message)


def create_agent_card() -> AgentCard:
    """Create agent card advertising rate limiting extension capability."""

    # Create base agent card
    agent_card = AgentCard(
        name="My Agent",
        description="An agent with rate limiting",
        url="http://localhost:9999/",
        capabilities=AgentCapabilities(streaming=True),
    )

    # Add rate limiting extension to advertise capability
    rate_limit_ext = RateLimitingExtension()
    agent_card = rate_limit_ext.add_to_card(agent_card)

    return agent_card


# Example of how responses differ with/without extension activation:

"""
WITHOUT EXTENSION (client doesn't send X-A2A-Extensions header):
- Rate limiting still happens (agent protection)
- Client gets error message but no structured usage data
- Response: {"message": {"parts": [{"text": "Rate limit exceeded..."}]}}

WITH EXTENSION (client sends X-A2A-Extensions header):
- Same rate limiting enforcement
- Client gets error message AND structured usage data
- Response includes metadata:
    {
        "message": {
            "parts": [{"text": "Rate limit exceeded..."}],
            "metadata": {
                "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result": {
                    "allowed": false,
                    "remaining": 0,
                    "retry_after": 15.3,
                    "reset_time": 1640995275.3,
                    "limit_type": "token_bucket"
                }
            }
        }
    }
"""
