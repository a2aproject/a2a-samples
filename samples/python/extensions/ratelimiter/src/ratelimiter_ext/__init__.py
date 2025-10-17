"""Rate Limiting Extension for A2A Protocol.

This extension provides comprehensive rate limiting capabilities for A2A agents,
supporting multiple algorithms and integration patterns following the A2A
extension specification.
"""

__version__ = "0.1.0"

from collections.abc import AsyncIterator, Callable
from typing import Any

from a2a.client import (
    Client,
    ClientCallInterceptor,
    ClientEvent,
    ClientFactory,
    Consumer,
)
from a2a.client.client_factory import TransportProducer
from a2a.client.middleware import ClientCallContext
from a2a.extensions.common import HTTP_EXTENSION_HEADER, find_extension_by_uri
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentCard,
    AgentExtension,
    GetTaskPushNotificationConfigParams,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message

from ratelimiter_ext.limiters import (
    CompositeLimiter,
    FixedWindowLimiter,
    RateLimiter,
    RateLimitResult,
    SlidingWindowLimiter,
    TokenBucketLimiter,
)

_CORE_PATH = "github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1"
URI = f"https://{_CORE_PATH}"
RATE_LIMIT_FIELD = f"{_CORE_PATH}/limits"
RATE_LIMIT_RESULT_FIELD = f"{_CORE_PATH}/result"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, result: RateLimitResult, message: str | None = None):
        self.result = result
        super().__init__(message or f"Rate limit exceeded. Retry after {result.retry_after}s")


class RateLimitingExtension:
    """A2A Rate Limiting Extension.

    This extension provides flexible rate limiting capabilities for A2A agents,
    supporting multiple algorithms and integration patterns. It follows the
    same design patterns as the official timestamp extension.
    """

    def __init__(
        self, limiter: RateLimiter | None = None, key_extractor: Callable[[RequestContext], str] | None = None
    ):
        """Initialize the rate limiting extension.

        Args:
            limiter: Rate limiting algorithm to use (defaults to TokenBucketLimiter)
            key_extractor: Function to extract rate limit key from context
        """
        self.limiter = limiter or TokenBucketLimiter()
        self.key_extractor = key_extractor or self._default_key_extractor

    def _default_key_extractor(self, context: RequestContext) -> str:
        """Default key extraction based on available context information."""
        # Try to extract from various context sources
        if hasattr(context, "client_id") and context.client_id:
            return f"client:{context.client_id}"
        elif hasattr(context, "remote_addr") and context.remote_addr:
            return f"ip:{context.remote_addr}"
        elif hasattr(context, "user_id") and context.user_id:
            return f"user:{context.user_id}"
        else:
            return "global:default"

    # Option 1: Let the developer do it themselves
    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=URI,
            description="Provides rate limiting capabilities for agent requests.",
        )

    # Option 2: Do it for them
    def add_to_card(self, card: AgentCard) -> AgentCard:
        """Add this extension to an AgentCard."""
        if not self.is_supported(card):
            if not (exts := card.capabilities.extensions):
                exts = card.capabilities.extensions = []
            exts.append(self.agent_extension())
        return card

    def is_supported(self, card: AgentCard | None) -> bool:
        """Returns whether this extension is supported by the AgentCard."""
        if card:
            return find_extension_by_uri(card, URI) is not None
        return False

    def activate(self, context: RequestContext) -> bool:
        """Activate this extension based on request context.

        The extension is considered active if the caller indicated it in an
        X-A2A-Extensions header.
        """
        if URI in context.requested_extensions:
            context.add_activated_extension(URI)
            return True
        return False

    # Option 1: Self-serve rate limiting
    def check_limit(self, context: RequestContext, limits: dict[str, Any]) -> RateLimitResult:
        """Check if request should be allowed under current rate limits.

        Args:
            context: Request context containing client information
            limits: Rate limiting configuration

        Returns:
            RateLimitResult indicating if request is allowed
        """
        key = self.key_extractor(context)

        # Extract limit configuration
        limit = limits.get("requests", 100)
        window = limits.get("window", 60)  # seconds

        return self.limiter.check_limit(key, limit, window)

    # Option 2: Assisted rate limiting
    def check_and_enforce(self, context: RequestContext, limits: dict[str, Any]) -> RateLimitResult:
        """Check rate limit and raise exception if exceeded."""
        result = self.check_limit(context, limits)
        if not result.allowed:
            raise RateLimitExceeded(result)
        return result

    def check_if_activated(self, context: RequestContext, limits: dict[str, Any]) -> RateLimitResult | None:
        """Check rate limit only if extension is activated."""
        if self.activate(context):
            return self.check_limit(context, limits)
        return None

    # Option 3: Add rate limit metadata to responses
    def add_rate_limit_headers(self, result: RateLimitResult, message: Message) -> None:
        """Add rate limit information to message metadata."""
        if message.metadata is None:
            message.metadata = {}

        message.metadata[RATE_LIMIT_RESULT_FIELD] = result.to_dict()

    # Option 4: Helper class
    def get_rate_limiter(self, context: RequestContext) -> "RateLimitHelper":
        """Get a helper class for rate limiting within request context."""
        active = self.activate(context)
        return RateLimitHelper(active, self, context)

    # Option 5: Fully managed via decorators
    def wrap_executor(self, executor: AgentExecutor) -> AgentExecutor:
        """Wrap executor with automatic rate limiting."""
        return _RateLimitedAgentExecutor(executor, self)

    def request_activation_http(self, http_kwargs: dict[str, Any]) -> dict[str, Any]:
        """Update http_kwargs to request activation of this extension."""
        if not (headers := http_kwargs.get("headers")):
            headers = http_kwargs["headers"] = {}
        header_val = URI
        if headers.get(HTTP_EXTENSION_HEADER):
            header_val = headers[HTTP_EXTENSION_HEADER] + ", " + URI
        headers[HTTP_EXTENSION_HEADER] = header_val
        return http_kwargs

    # Client-side support
    def wrap_client(self, client: Client) -> Client:
        """Returns a Client that respects rate limits for outgoing requests."""
        return _RateLimitedClient(client, self)

    def client_interceptor(self) -> ClientCallInterceptor:
        """Get a client interceptor that enforces rate limiting."""
        return _RateLimitingClientInterceptor(self)

    def wrap_client_factory(self, factory: ClientFactory) -> ClientFactory:
        """Returns a ClientFactory that handles rate limiting."""
        return _RateLimitClientFactory(factory, self)

    def reset_limits(self, key: str) -> None:
        """Reset rate limit state for a specific key."""
        self.limiter.reset(key)


class RateLimitHelper:
    """Helper class for rate limiting within a request context."""

    def __init__(self, active: bool, ext: RateLimitingExtension, context: RequestContext):
        self._active = active
        self._ext = ext
        self._context = context

    def check_limit(self, limits: dict[str, Any]) -> RateLimitResult | None:
        """Check rate limit if active."""
        if self._active:
            return self._ext.check_limit(self._context, limits)
        return None

    def enforce_limit(self, limits: dict[str, Any]) -> RateLimitResult | None:
        """Check and enforce rate limit if active."""
        if self._active:
            return self._ext.check_and_enforce(self._context, limits)
        return None


class _RateLimitedAgentExecutor(AgentExecutor):
    """AgentExecutor decorator that applies rate limiting."""

    def __init__(self, delegate: AgentExecutor, ext: RateLimitingExtension):
        self._delegate = delegate
        self._ext = ext

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Check rate limits if extension is activated
        if self._ext.activate(context):
            # Extract rate limits from message metadata or use defaults
            limits = self._extract_limits(context)
            try:
                result = self._ext.check_and_enforce(context, limits)
                # Add rate limit info to responses
                event_queue = _RateLimitedEventQueue(event_queue, self._ext, result)
            except RateLimitExceeded as e:
                # Send rate limit exceeded response
                error_message = f"Rate limit exceeded. {e.result.remaining} requests remaining. "
                if e.result.retry_after:
                    error_message += f"Retry after {e.result.retry_after:.1f} seconds."

                await event_queue.enqueue_event(new_agent_text_message(error_message))
                return

        # Proceed with normal execution
        await self._delegate.execute(context, event_queue)

    def _extract_limits(self, context: RequestContext) -> dict[str, Any]:
        """Extract rate limiting configuration from context."""
        default_limits = {"requests": 100, "window": 60}

        if not context.message or not context.message.metadata:
            return default_limits

        # Look for rate limit configuration in message metadata
        limits = context.message.metadata.get(RATE_LIMIT_FIELD, {})
        return {**default_limits, **limits}

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await self._delegate.cancel(context, event_queue)


class _RateLimitedEventQueue(EventQueue):
    """EventQueue decorator that adds rate limit headers to responses."""

    def __init__(
        self,
        delegate: EventQueue,
        ext: RateLimitingExtension,
        result: RateLimitResult,
    ):
        self._delegate = delegate
        self._ext = ext
        self._result = result

    async def enqueue_event(
        self,
        event: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
    ) -> None:
        # Add rate limit headers to messages
        if isinstance(event, Message):
            self._ext.add_rate_limit_headers(self._result, event)
        elif isinstance(event, TaskStatusUpdateEvent) and event.status.message:
            self._ext.add_rate_limit_headers(self._result, event.status.message)

        await self._delegate.enqueue_event(event)

    # Delegate all other methods
    async def dequeue_event(
        self, no_wait: bool = False
    ) -> Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent:
        return await self._delegate.dequeue_event(no_wait)

    async def close(self) -> None:
        return await self._delegate.close()

    def tap(self) -> EventQueue:
        return self._delegate.tap()

    def is_closed(self) -> bool:
        return self._delegate.is_closed()

    def task_done(self) -> None:
        return self._delegate.task_done()


class _RateLimitedClient(Client):
    """Client decorator that applies rate limiting to outgoing requests."""

    def __init__(self, delegate: Client, ext: RateLimitingExtension):
        self._delegate = delegate
        self._ext = ext

    async def send_message(
        self,
        request: Message,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[ClientEvent | Message]:
        # Apply client-side rate limiting here if needed
        # For now, just delegate
        async for e in self._delegate.send_message(request, context=context):
            yield e

    # Delegate all other methods
    async def get_task(
        self,
        request: TaskQueryParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate.get_task(request, context=context)

    async def cancel_task(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        return await self._delegate.cancel_task(request, context=context)

    async def set_task_callback(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.set_task_callback(request, context=context)

    async def get_task_callback(
        self,
        request: GetTaskPushNotificationConfigParams,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        return await self._delegate.get_task_callback(request, context=context)

    async def resubscribe(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[ClientEvent]:
        async for e in self._delegate.resubscribe(request, context=context):
            yield e

    async def get_card(self, *, context: ClientCallContext | None = None) -> AgentCard:
        return await self._delegate.get_card(context=context)


class _RateLimitingClientInterceptor(ClientCallInterceptor):
    """Client interceptor that handles rate limiting for outgoing requests."""

    def __init__(self, ext: RateLimitingExtension):
        self._ext = ext

    async def intercept(
        self,
        _method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: AgentCard | None,
        _context: ClientCallContext | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._ext.is_supported(agent_card):
            return (request_payload, http_kwargs)

        # Request activation of rate limiting extension
        return (
            request_payload,
            self._ext.request_activation_http(http_kwargs),
        )


class _RateLimitClientFactory(ClientFactory):
    """ClientFactory decorator that adds rate limiting support."""

    def __init__(self, delegate: ClientFactory, ext: RateLimitingExtension):
        self._delegate = delegate
        self._ext = ext

    def register(self, label: str, generator: TransportProducer) -> None:
        self._delegate.register(label, generator)

    def create(
        self,
        card: AgentCard,
        consumers: list[Consumer] | None = None,
        interceptors: list[ClientCallInterceptor] | None = None,
    ) -> Client:
        interceptors = interceptors or []
        interceptors.append(self._ext.client_interceptor())
        return self._delegate.create(card, consumers, interceptors)


__all__ = [
    "RATE_LIMIT_FIELD",
    "RATE_LIMIT_RESULT_FIELD",
    "URI",
    "CompositeLimiter",
    "FixedWindowLimiter",
    "RateLimitExceeded",
    "RateLimitHelper",
    "RateLimitResult",
    "RateLimiter",
    "RateLimitingExtension",
    "SlidingWindowLimiter",
    "TokenBucketLimiter",
]
