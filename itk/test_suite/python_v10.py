import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


HTTP_PORT = '10104'
GRPC_PORT = '11004'


def _spawn_agent() -> None:
    log_file = open(_ROOT_DIR / 'python_v10_v03_compat.log', 'w')
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
        cwd=_ROOT_DIR / 'agents/python/v10',
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


AGENT_DEF = {
    'launcher': _spawn_agent,
    'httpPort': HTTP_PORT,
    'grpcPort': GRPC_PORT,
}
