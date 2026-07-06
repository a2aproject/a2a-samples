import httpx

# ruff: noqa: S101, INP001
import pytest

from trace_trust_ext import A2AMessage, TraceTrustExtension


# Helper to mock the next handler
async def mock_next_handler(message: A2AMessage) -> str:
    return 'success'


@pytest.fixture
def a2a_message() -> A2AMessage:
    return A2AMessage(metadata={'task': 'test_task'})


@pytest.mark.asyncio
async def test_trusted_caller(a2a_message: A2AMessage) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'data': {'reputation': {'score': 0.8}}})

    transport = httpx.MockTransport(handler)

    async with TraceTrustExtension(api_key='fake_key', min_score=0.35) as middleware:
        middleware.client = httpx.AsyncClient(transport=transport)

        result = await middleware.server_middleware(mock_next_handler, a2a_message, 'trusted_id')
        assert result == 'success'


@pytest.mark.asyncio
async def test_rejected_below_threshold(a2a_message: A2AMessage) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'data': {'reputation': {'score': 0.2}}})

    transport = httpx.MockTransport(handler)

    async with TraceTrustExtension(api_key='fake_key', min_score=0.35) as middleware:
        middleware.client = httpx.AsyncClient(transport=transport)

        with pytest.raises(PermissionError, match='Access Denied: Sender reputation'):
            await middleware.server_middleware(mock_next_handler, a2a_message, 'untrusted_id')


@pytest.mark.asyncio
async def test_allow_when_fail_closed_is_false(a2a_message: A2AMessage) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Simulate network error or 500 error
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)

    async with TraceTrustExtension(
        api_key='fake_key', min_score=0.35, fail_closed=False
    ) as middleware:
        middleware.client = httpx.AsyncClient(transport=transport)

        # Should permit request because fail_closed=False
        result = await middleware.server_middleware(mock_next_handler, a2a_message, 'unknown_id')
        assert result == 'success'


@pytest.mark.asyncio
async def test_deny_when_fail_closed_is_true(a2a_message: A2AMessage) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Simulate network error or 500 error
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)

    async with TraceTrustExtension(
        api_key='fake_key', min_score=0.35, fail_closed=True
    ) as middleware:
        middleware.client = httpx.AsyncClient(transport=transport)

        # Should block request because fail_closed=True
        with pytest.raises(
            PermissionError,
            match=r'TRACE API unreachable and fail_closed is True\. Denying access\.',
        ):
            await middleware.server_middleware(mock_next_handler, a2a_message, 'unknown_id')


@pytest.mark.asyncio
async def test_handle_missing_score_field(a2a_message: A2AMessage) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                'data': {
                    'reputation': {
                        # Missing "score"
                    }
                }
            },
        )

    transport = httpx.MockTransport(handler)

    async with TraceTrustExtension(
        api_key='fake_key', min_score=0.35, fail_closed=True
    ) as middleware:
        middleware.client = httpx.AsyncClient(transport=transport)

        # Missing score triggers exception which triggers fail_closed
        with pytest.raises(
            PermissionError,
            match=r'TRACE API unreachable and fail_closed is True\. Denying access\.',
        ):
            await middleware.server_middleware(mock_next_handler, a2a_message, 'unknown_id')
