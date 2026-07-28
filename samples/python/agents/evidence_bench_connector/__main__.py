"""Run the Evidence Bench connector on loopback."""

import os

import uvicorn

from evidence_bench_connector.agent_executor import (
    ConnectorError,
    EvidenceBenchRemoteRunner,
)
from evidence_bench_connector.server import create_app


def main() -> None:
    """Load non-secret routing settings and start the local connector."""
    host = os.environ.get('EVIDENCE_BENCH_CONNECTOR_HOST', '127.0.0.1')
    port = int(os.environ.get('EVIDENCE_BENCH_CONNECTOR_PORT', '9999'))
    public_url = os.environ.get(
        'EVIDENCE_BENCH_CONNECTOR_PUBLIC_URL',
        f'http://127.0.0.1:{port}',
    )
    remote = EvidenceBenchRemoteRunner(
        base_url=os.environ.get('EVIDENCE_BENCH_URL', 'http://127.0.0.1:8080'),
        token=os.environ.get('EVIDENCE_BENCH_A2A_TOKEN', ''),
    )
    uvicorn.run(create_app(remote, public_url), host=host, port=port)


if __name__ == '__main__':
    try:
        main()
    except (ConnectorError, ValueError) as exc:
        raise SystemExit(str(exc)) from None
