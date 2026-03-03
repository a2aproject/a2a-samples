import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


HTTP_PORT = '10101'
GRPC_PORT = '11001'


def _spawn_agent() -> None:
    return subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            'go',
            'run',
            'main.go',
            '--httpPort',
            HTTP_PORT,
            '--grpcPort',
            GRPC_PORT,
        ],
        cwd=_ROOT_DIR / 'agents/go/v03',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


AGENT_DEF = {
    'launcher': _spawn_agent,
    'httpPort': HTTP_PORT,
    'grpcPort': GRPC_PORT,
}
