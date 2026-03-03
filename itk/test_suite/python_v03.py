import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


HTTP_PORT = '10102'
GRPC_PORT = '11002'


def _spawn_agent() -> None:
    return subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            'uv',
            'run',
            'main.py',
            '--httpPort',
            HTTP_PORT,
            '--grpcPort',
            GRPC_PORT,
        ],
        cwd=_ROOT_DIR / 'agents/python/v03',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


AGENT_DEF = {
    'launcher': _spawn_agent,
    'httpPort': HTTP_PORT,
    'grpcPort': GRPC_PORT,
}
