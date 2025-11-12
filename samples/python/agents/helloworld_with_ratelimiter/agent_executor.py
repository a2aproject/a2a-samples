from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from ratelimiter_ext import RateLimitingExtension, TokenBucketLimiter


# --8<-- [start:HelloWorldAgent]
class HelloWorldAgent:
    """Hello World Agent."""

    async def invoke(self) -> str:
        """Invoke the agent to return a greeting."""
        return 'Hello World'


# --8<-- [end:HelloWorldAgent]


# --8<-- [start:HelloWorldAgentExecutor_init]
class HelloWorldAgentExecutor(AgentExecutor):
    """HelloWorld agent executor with rate limiting enforcement.

    This executor demonstrates the minimal changes needed to add rate limiting:
    - Rate limiting ENFORCEMENT: Always active (protects agent resources)
    - Rate limiting COMMUNICATION: Conditional (provides usage signals to clients)

    The rate limiter is used for enforcement (always happens).
    The extension is used for communication (only when client requests it).
    """

    def __init__(
        self,
        rate_limiter: TokenBucketLimiter,
        rate_limit_extension: RateLimitingExtension,
    ) -> None:
        """Initialize the HelloWorld agent executor.

        Args:
            rate_limiter: Rate limiter for enforcement (always active)
            rate_limit_extension: Extension for communicating usage signals
        """
        self.agent = HelloWorldAgent()
        self.rate_limiter = rate_limiter
        self.rate_limit_extension = rate_limit_extension

    # --8<-- [end:HelloWorldAgentExecutor_init]

    def _extract_client_key(self, context: RequestContext) -> str:
        """Extract unique client identifier for rate limiting.

        In production, use OAuth tokens, API keys, or other authenticated
        identity mechanisms instead of IP addresses.

        Args:
            context: Request context

        Returns:
            Unique key for rate limiting this client
        """
        remote_addr = getattr(context, 'remote_addr', 'unknown')
        return f'ip:{remote_addr}'

    # --8<-- [start:HelloWorldAgentExecutor_execute]
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent with rate limiting enforcement.

        Rate limiting is ALWAYS enforced, regardless of extension activation.
        Extension activation only controls whether usage signals are included
        in the response.

        Flow:
        1. Extract client identity
        2. Check rate limits (enforcement)
        3. If rate limited, return error (optionally with usage signals)
        4. If allowed, process request normally (optionally with usage signals)
        """
        # Step 1: Extract client identity
        client_key = self._extract_client_key(context)

        # Step 2: ALWAYS check rate limits (enforcement)
        # Rate limit: 10 requests per minute
        usage = self.rate_limiter.check_limit(
            key=client_key, limit=10, window=60
        )

        # Step 3: If rate limited, return error
        if not usage.allowed:
            error_msg = (
                f'Rate limit exceeded. {usage.remaining} requests remaining. '
                f'Retry after {usage.retry_after:.1f} seconds.'
            )
            message = new_agent_text_message(error_msg)

            # Extension: Add usage signals if client requested them
            if self.rate_limit_extension.is_activated(context):
                self.rate_limit_extension.add_usage_signals(message, usage)

            await event_queue.enqueue_event(message)
            return

        # Step 4: Process request normally (rate limit passed)
        result = await self.agent.invoke()
        message = new_agent_text_message(result)

        # Extension: Add usage signals if client requested them
        if self.rate_limit_extension.is_activated(context):
            self.rate_limit_extension.add_usage_signals(message, usage)

        await event_queue.enqueue_event(message)

    # --8<-- [end:HelloWorldAgentExecutor_execute]

    # --8<-- [start:HelloWorldAgentExecutor_cancel]
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the agent execution (not supported)."""
        msg = 'cancel not supported'
        raise NotImplementedError(msg)

    # --8<-- [end:HelloWorldAgentExecutor_cancel]
