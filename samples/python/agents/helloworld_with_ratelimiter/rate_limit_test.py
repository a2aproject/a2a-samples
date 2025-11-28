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
    ) -> dict[str, Any]:
        """Send a single request to the agent.

        Args:
            message_text: The text message to send
            use_extension: Whether to activate the rate limiting extension
                (requests usage signals in response)
        """
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
        """Test rate limiting WITHOUT extension activation.

        This demonstrates that rate limiting enforcement happens regardless
        of extension activation. The extension only controls visibility.
        """
        print('🧪 Testing Rate Limiting WITHOUT Extension')
        print('=' * 60)
        print('Rate limiting is enforced, but no usage signals in responses.')
        print('(Extension controls communication, not enforcement)\n')

        start_time = time.time()

        # Send 15 rapid requests WITHOUT extension activation
        # Rate limiting still happens!
        for i in range(1, 16):
            response = await self.send_request(
                f'Hello #{i}',
                use_extension=False,  # No extension - but still rate limited!
            )
            self.print_response_info(i, response, start_time)

            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)

        print(f'\n⏱️  Total time: {time.time() - start_time:.1f}s')
        print('\n💡 Key Insight: Rate limiting worked WITHOUT the extension!')
        print('   The extension only adds usage signals, not enforcement.')

    async def test_with_extension_signals(self):
        """Test WITH extension activation to see usage signals.

        Same rate limiting enforcement, but now we get visibility into
        our usage through the extension's communication protocol.
        """
        print('\n\n🧪 Testing WITH Extension (Usage Signals Included)')
        print('=' * 60)
        print(
            'Same rate limiting (10 req/min), but now responses include usage info.'
        )
        print('(Extension provides visibility into enforcement)\n')

        start_time = time.time()

        # Send 8 requests WITH extension activation
        # Rate limiting still enforced, but now we see usage signals
        for i in range(1, 9):
            response = await self.send_request(
                f'With signals #{i}',
                use_extension=True,
            )
            self.print_response_info(i, response, start_time)
            await asyncio.sleep(0.1)

        print(f'\n⏱️  Total time: {time.time() - start_time:.1f}s')
        print(
            '\n💡 Key Insight: Now we see remaining requests, retry timing, etc.'
        )
        print('   Extension gives us visibility without changing enforcement.')
        print('   Server controls the rate limits, not the client.')

    async def test_recovery_after_wait(self):
        """Test that rate limits recover after waiting.

        Token bucket continuously refills, so waiting allows recovery.
        Server enforces 10 requests per minute (configured in agent).
        """
        print('\n\n🧪 Testing Rate Limit Recovery')
        print('=' * 60)
        print('Server enforces 10 requests per minute with token bucket.')
        print('Tokens refill continuously - waiting allows recovery.\n')

        # Exhaust the limit
        print('Step 1: Make rapid requests to exhaust rate limit')
        for i in range(1, 13):
            response = await self.send_request(
                f'Exhaust #{i}', use_extension=True
            )
            rate_info = self.extract_rate_limit_info(response)
            is_limited = (
                'rate limit exceeded' in rate_info['message_text'].lower()
            )
            status = '🚫 Limited' if is_limited else '✅ Success'
            print(
                f'   Request {i}: {status} (Remaining: {rate_info.get("remaining", "N/A")})'
            )
            await asyncio.sleep(0.05)

        # Wait for recovery
        wait_time = 10
        print(f'\nStep 2: Waiting {wait_time} seconds for token refill...')
        await asyncio.sleep(wait_time)

        # Test recovery
        print('Step 3: Test recovery (tokens should have refilled)')
        for i in range(1, 4):
            response = await self.send_request(
                f'Recovery #{i}',
                use_extension=True,
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

        print('\n💡 Key Insight: Token bucket refills continuously.')
        print('   Waiting allows tokens to accumulate back up to capacity.')

    async def run_all_tests(self):
        """Run all rate limiting tests."""
        print('🚀 Rate Limiting Usage Signals Extension Test Suite')
        print('=' * 60)
        print('Testing HelloWorld agent with rate limiting')
        print('Agent URL:', self.base_url)
        print()
        print('This test suite demonstrates:')
        print('1. Rate limiting enforcement (always active)')
        print('2. Extension communication (optional visibility)')
        print('3. Separation of enforcement vs. signals')
        print()

        try:
            await self.test_basic_rate_limiting()
            await self.test_with_extension_signals()
            await self.test_recovery_after_wait()

            print('\n' + '=' * 60)
            print('✅ All tests completed!')
            print('\nKey Learnings:')
            print('- Rate limiting ALWAYS enforced by server (protects agent)')
            print('- Extension = visibility, NOT enforcement')
            print('- Clients get usage info when they activate extension')
            print('- Server controls all policies (clients cannot set limits)')
            print(
                '- Token bucket allows burst traffic while maintaining steady rate'
            )

        except (KeyError, ValueError, RuntimeError) as e:
            print(f'\n❌ Test failed with error: {e}')
        finally:
            await self.client.aclose()


async def main():
    """Main function to run the rate limiting tests."""

    parser = argparse.ArgumentParser(
        description='Test rate limiting and usage signals extension',
        epilog='This demonstrates the separation of enforcement (always active) '
        'vs. communication (extension provides visibility)',
    )
    parser.add_argument(
        '--url',
        default='http://localhost:9999',
        help='Agent URL (default: http://localhost:9999)',
    )
    parser.add_argument(
        '--test',
        choices=['basic', 'extension', 'recovery', 'all'],
        default='all',
        help='Which test to run: basic (no extension), extension (with usage signals), '
        'recovery (token refill), or all (default: all)',
    )

    args = parser.parse_args()

    client = RateLimitTestClient(args.url)

    try:
        if args.test == 'basic':
            await client.test_basic_rate_limiting()
        elif args.test == 'extension':
            await client.test_with_extension_signals()
        elif args.test == 'recovery':
            await client.test_recovery_after_wait()
        else:
            await client.run_all_tests()
    finally:
        await client.client.aclose()


if __name__ == '__main__':
    asyncio.run(main())
