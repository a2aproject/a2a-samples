import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


def spawn_agent(http_port: int, grpc_port: int) -> subprocess.Popen:
    """Spawns the Python v0.3 agent process.

    Args:
        http_port: The port for the HTTP/JSON-RPC interface.
        grpc_port: The port for the gRPC interface.

    Returns:
        subprocess.Popen: The spawned process object.
    """
    return subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            'uv',
            'run',
            'main.py',
            '--httpPort',
            str(http_port),
            '--grpcPort',
            str(grpc_port),
        ],
        cwd=_ROOT_DIR / 'agents/python/v03',
        stderr=subprocess.STDOUT,
        text=True,
    )
