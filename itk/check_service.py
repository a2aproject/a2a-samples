import asyncio
import json

import httpx


async def _test_run() -> None:
    url = 'http://0.0.0.0:8000/run'
    payload = {
        'tests': [
            {
                'name': 'v03-core-mini',
                'sdks': ['python_v03', 'go_v03'],
                'traversal': 'euler',
                'protocols': ['jsonrpc'],
            },
            {
                'name': 'v10-core-mini',
                'sdks': ['python_v10', 'go_v10'],
                'traversal': 'euler',
                'protocols': ['http_json'],
            },
        ]
    }

    print(f'Sending request to {url}...')
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print('Response received successfully:')
            print(json.dumps(response.json(), indent=2))
        except httpx.HTTPStatusError as e:
            print(f'HTTP error occurred: {e}')
            print(f'Response: {e.response.text}')
        except httpx.RequestError as e:
            print(f'Request error occurred: {e}')
        except Exception as e:  # noqa: BLE001
            print(f'An error occurred: {e}')


if __name__ == '__main__':
    asyncio.run(_test_run())
