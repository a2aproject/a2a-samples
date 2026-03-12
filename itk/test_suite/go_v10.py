import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


HTTP_PORT = '10103'
GRPC_PORT = '11003'


def _spawn_agent() -> subprocess.Popen:
    log_file = (_ROOT_DIR / 'go_v10.log').open('w')
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
        cwd=_ROOT_DIR / 'agents/go/v10',
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


AGENT_DEF = {
    'launcher': _spawn_agent,
    'httpPort': HTTP_PORT,
    'grpcPort': GRPC_PORT,
}
