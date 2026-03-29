"""Rate Limiting Usage Signals Extension for A2A Protocol.

This extension defines a standard way for A2A agents to communicate rate limiting
information to clients. The extension does NOT enforce rate limits - agents should
implement rate limiting independently. Instead, this extension provides a protocol
for sharing usage data (remaining quota, retry timing, etc.) with clients.

Key Concepts:
    - Rate limiting enforcement: Agent's responsibility (always active)
    - Extension purpose: Communication of usage signals to clients
    - Extension activation: Signal from client saying "I want usage info"

For rate limiting enforcement, use the TokenBucketLimiter or your own rate limiter.
This extension only handles communication of that state back to the client.
"""

__version__ = "0.1.0"

from a2a.extensions.common import find_extension_by_uri
from a2a.server.agent_execution import RequestContext
from a2a.types import (
    AgentCard,
    AgentExtension,
    Message,
)

from ratelimiter_ext.limiters import (
    RateLimitResult,
    TokenBucketLimiter,
)

_CORE_PATH = "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1"
URI = f"https://{_CORE_PATH}"
RATE_LIMIT_RESULT_FIELD = f"{_CORE_PATH}/result"


class RateLimitingExtension:
    """A2A Rate Limiting Usage Signals Extension.

    This extension provides a standard protocol for agents to communicate rate
    limiting information to clients. It does NOT enforce rate limits - that is
    the agent's responsibility.

    Purpose:
        - Communicate rate limit usage to clients
        - Provide visibility into remaining quota
        - Inform clients when to retry

    NOT in scope:
        - Enforcing rate limits (agent does this)
        - Determining rate limit policies (agent does this)
        - Client-side rate limiting

    Example Usage:
        # In your agent executor __init__:
        self.rate_limit_ext = RateLimitingExtension()
        self.rate_limiter = TokenBucketLimiter()  # For enforcement

        # In your agent executor execute():
        # 1. Always enforce rate limits
        usage = self.rate_limiter.check_limit(client_key, limit, window)
        if not usage.allowed:
            message = new_agent_text_message("Rate limit exceeded")
            # 2. Add signals if client requested them
            if self.rate_limit_ext.is_activated(context):
                self.rate_limit_ext.add_usage_signals(message, usage)
            await event_queue.enqueue_event(message)
            return

        # 3. Process request normally
        result = await self.agent.invoke()
        message = new_agent_text_message(result)

        # 4. Add signals if client requested them
        if self.rate_limit_ext.is_activated(context):
            self.rate_limit_ext.add_usage_signals(message, usage)

        await event_queue.enqueue_event(message)
    """

    def __init__(self):
        """Initialize the rate limiting extension.

        No configuration needed - this extension only handles communication,
        not enforcement.
        """
        pass

    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension metadata for this extension."""
        return AgentExtension(
            uri=URI,
            description="Communicates rate limit usage signals to clients.",
        )

    def add_to_card(self, card: AgentCard) -> AgentCard:
        """Add this extension to an AgentCard.

        This advertises that the agent supports communicating rate limit
        information to clients that request it.

        Args:
            card: The AgentCard to add the extension to

        Returns:
            Updated AgentCard with extension added
        """
        if not self.is_supported(card):
            if card.capabilities.extensions is None:
                card.capabilities.extensions = []
            card.capabilities.extensions.append(self.agent_extension())
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Check if this extension is advertised in the AgentCard.

        Args:
            card: The AgentCard to check

        Returns:
            True if extension is supported, False otherwise
        """
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    def is_activated(self, context: RequestContext) -> bool:
        """Check if client requested rate limit usage signals.

        The extension is activated when the client includes it in the
        X-A2A-Extensions header, indicating they want to receive usage
        information in responses.

        Args:
            context: The request context

        Returns:
            True if client wants usage signals, False otherwise
        """
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    def add_usage_signals(self, message: Message, usage: RateLimitResult) -> None:
        """Add rate limit usage information to message metadata.

        This should only be called if the client activated the extension
        (use is_activated() to check).

        Args:
            message: The message to add usage signals to
            usage: The rate limit usage information to include
        """
        if message.metadata is None:
            message.metadata = {}

        message.metadata[RATE_LIMIT_RESULT_FIELD] = usage.to_dict()


__all__ = [
    "RATE_LIMIT_RESULT_FIELD",
    "URI",
    "RateLimitResult",
    "RateLimitingExtension",
    "TokenBucketLimiter",
]
