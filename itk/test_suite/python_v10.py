import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


def spawn_agent(http_port: int, grpc_port: int) -> subprocess.Popen:
    """Spawns the Python v1.0 agent process.

    This function updates the `uv.lock` file before spawning the process.

    Args:
        http_port: The port for the HTTP/JSON-RPC interface.
        grpc_port: The port for the gRPC interface.

    Returns:
        subprocess.Popen: The spawned process object.
    """
    subprocess.run(
        [  # noqa: S607
            'uv',
            'lock',
            '--upgrade',
        ],
        cwd=_ROOT_DIR / 'agents/python/v10',
        check=True,
    )
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
        cwd=_ROOT_DIR / 'agents/python/v10',
        stderr=subprocess.STDOUT,
        text=True,
    )
