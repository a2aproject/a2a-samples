#!/usr/bin/env python3
"""Rate Limiting Test Client for HelloWorld Agent.

This client demonstrates the rate limiting extension by making multiple
rapid requests and showing how the rate limiting behavior works.
"""

import argparse
import asyncio
import time

from typing import Any

import httpx


class RateLimitTestClient:
    """Test client for demonstrating rate limiting behavior."""

    def __init__(self, base_url: str = 'http://localhost:9999'):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def send_request(
        self,
        message_text: str = 'Hello',
        use_extension: bool = False,
        custom_limits: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Send a single request to the agent."""
        payload = {
            'jsonrpc': '2.0',
            'id': f'test-{int(time.time() * 1000)}',
            'method': 'message/send',
            'params': {
                'message': {
                    'kind': 'message',
                    'messageId': f'msg-{int(time.time() * 1000)}',
                    'parts': [{'kind': 'text', 'text': message_text}],
                    'role': 'user',
                }
            },
        }

        headers = {'Content-Type': 'application/json'}

        # Add extension activation if requested
        if use_extension:
            headers['X-A2A-Extensions'] = (
                'https://github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1'
            )

            if custom_limits:
                payload['params']['message']['metadata'] = {
                    'github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/limits': custom_limits
                }

        try:
            response = await self.client.post(
                self.base_url, json=payload, headers=headers, timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            return {'error': f'Request failed: {e}'}
        except httpx.HTTPStatusError as e:
            return {
                'error': f'HTTP {e.response.status_code}: {e.response.text}'
            }

    def extract_rate_limit_info(
        self, response: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract rate limit information from response metadata."""
        try:
            message = response.get('result', {}).get('message', {})
            metadata = message.get('metadata', {})
            rate_limit_result = metadata.get(
                'github.com/a2aproject/a2a-samples/extensions/ratelimiter/v1/result',
                {},
            )

            return {
                'allowed': rate_limit_result.get('allowed'),
                'remaining': rate_limit_result.get('remaining'),
                'limit_type': rate_limit_result.get('limit_type'),
                'retry_after': rate_limit_result.get('retry_after'),
                'message_text': message.get('parts', [{}])[0].get('text', ''),
            }
        except (KeyError, IndexError):
            return {'error': 'Could not extract rate limit info'}

    def print_response_info(
        self, response_num: int, response: dict[str, Any], start_time: float
    ):
        """Print formatted response information."""
        elapsed = time.time() - start_time
        rate_limit_info = self.extract_rate_limit_info(response)

        print(f'\n--- Response {response_num} (t={elapsed:.1f}s) ---')

        if 'error' in response:
            print(f'❌ Error: {response["error"]}')
            return

        if 'error' in rate_limit_info:
            print(f'⚠️  {rate_limit_info["error"]}')
            return

        message_text = rate_limit_info['message_text']
        is_rate_limited = 'rate limit exceeded' in message_text.lower()

        if is_rate_limited:
            print(f'🚫 Rate Limited: {message_text}')
        else:
            print(f'✅ Success: {message_text}')

        if rate_limit_info['allowed'] is not None:
            print(f'   Remaining: {rate_limit_info["remaining"]}')
            print(f'   Algorithm: {rate_limit_info["limit_type"]}')

            if rate_limit_info['retry_after']:
                print(f'   Retry after: {rate_limit_info["retry_after"]:.1f}s')

    async def test_basic_rate_limiting(self):
        """Test basic rate limiting with default settings."""
        print('🧪 Testing Basic Rate Limiting (Default Settings)')
        print('=' * 60)

        start_time = time.time()

        # Send 15 rapid requests to trigger rate limiting
        for i in range(1, 16):
            response = await self.send_request(f'Hello #{i}')
            self.print_response_info(i, response, start_time)

            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)

        print(f'\n⏱️  Total time: {time.time() - start_time:.1f}s')

    async def test_custom_limits(self):
        """Test with custom rate limits via extension activation."""
        print('\n\n🧪 Testing Custom Rate Limits (5 requests/minute)')
        print('=' * 60)

        custom_limits = {'requests': 5, 'window': 60}
        start_time = time.time()

        # Send 8 requests with custom limits
        for i in range(1, 9):
            response = await self.send_request(
                f'Custom limit test #{i}',
                use_extension=True,
                custom_limits=custom_limits,
            )
            self.print_response_info(i, response, start_time)
            await asyncio.sleep(0.1)

        print(f'\n⏱️  Total time: {time.time() - start_time:.1f}s')

    async def test_recovery_after_wait(self):
        """Test that rate limits recover after waiting."""
        print('\n\n🧪 Testing Rate Limit Recovery')
        print('=' * 60)

        custom_limits = {
            'requests': 3,
            'window': 10,
        }  # 3 requests per 10 seconds

        # Exhaust the limit
        print('Step 1: Exhaust rate limit (3 requests)')
        for i in range(1, 5):
            response = await self.send_request(
                f'Exhaust #{i}', use_extension=True, custom_limits=custom_limits
            )
            rate_info = self.extract_rate_limit_info(response)
            is_limited = (
                'rate limit exceeded' in rate_info['message_text'].lower()
            )
            status = '🚫 Limited' if is_limited else '✅ Success'
            print(
                f'   Request {i}: {status} (Remaining: {rate_info.get("remaining", "N/A")})'
            )
            await asyncio.sleep(0.1)

        # Wait for recovery
        wait_time = 12  # Wait longer than the window
        print(
            f'\nStep 2: Waiting {wait_time} seconds for rate limit recovery...'
        )
        await asyncio.sleep(wait_time)

        # Test recovery
        print('Step 3: Test recovery (should work again)')
        for i in range(1, 3):
            response = await self.send_request(
                f'Recovery #{i}',
                use_extension=True,
                custom_limits=custom_limits,
            )
            rate_info = self.extract_rate_limit_info(response)
            is_limited = (
                'rate limit exceeded' in rate_info['message_text'].lower()
            )
            status = '🚫 Limited' if is_limited else '✅ Success'
            print(
                f'   Request {i}: {status} (Remaining: {rate_info.get("remaining", "N/A")})'
            )
            await asyncio.sleep(0.1)

    async def run_all_tests(self):
        """Run all rate limiting tests."""
        print('🚀 Rate Limiting Extension Test Suite')
        print('=' * 60)
        print('Testing HelloWorld agent with rate limiting extension')
        print('Agent URL:', self.base_url)
        print()

        try:
            await self.test_basic_rate_limiting()
            await self.test_custom_limits()
            await self.test_recovery_after_wait()

            print('\n' + '=' * 60)
            print('✅ All tests completed!')
            print('\nKey Observations:')
            print('- Rate limiting prevents excessive requests')
            print('- Extension metadata provides limit information')
            print('- Different algorithms and limits can be configured')
            print('- Limits recover after waiting the specified window')
            print('- Error messages include retry timing information')

        except (KeyError, ValueError, RuntimeError) as e:
            print(f'\n❌ Test failed with error: {e}')
        finally:
            await self.client.aclose()


async def main():
    """Main function to run the rate limiting tests."""

    parser = argparse.ArgumentParser(description='Test rate limiting extension')
    parser.add_argument(
        '--url',
        default='http://localhost:9999',
        help='Agent URL (default: http://localhost:9999)',
    )
    parser.add_argument(
        '--test',
        choices=['basic', 'custom', 'recovery', 'all'],
        default='all',
        help='Which test to run (default: all)',
    )

    args = parser.parse_args()

    client = RateLimitTestClient(args.url)

    try:
        if args.test == 'basic':
            await client.test_basic_rate_limiting()
        elif args.test == 'custom':
            await client.test_custom_limits()
        elif args.test == 'recovery':
            await client.test_recovery_after_wait()
        else:
            await client.run_all_tests()
    finally:
        await client.client.aclose()


if __name__ == '__main__':
    asyncio.run(main())
