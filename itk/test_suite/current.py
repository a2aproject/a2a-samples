import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


def spawn_agent(http_port: int, grpc_port: int) -> subprocess.Popen:
    """Spawns the 'current' agent process by detecting its type.

    Args:
        http_port: The port for the HTTP/JSON-RPC interface.
        grpc_port: The port for the gRPC interface.

    Returns:
        subprocess.Popen: The spawned process object.

    Raises:
        RuntimeError: If the 'current' agent directory is not found or type cannot be determined.
    """
    current_dir = _ROOT_DIR / 'agents' / 'repo' / 'itk'
    if not current_dir.exists():
        raise RuntimeError(
            'current agent has not been mounted and is not available to test'
        )

    if (current_dir / 'main.go').exists():
        # Go agent
        return subprocess.Popen(  # noqa: S603
            [  # noqa: S607
                'go',
                'run',
                'main.go',
                '--httpPort',
                str(http_port),
                '--grpcPort',
                str(grpc_port),
            ],
            cwd=current_dir,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if (current_dir / 'main.py').exists():
        # Python agent
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
            cwd=current_dir,
            stderr=subprocess.STDOUT,
            text=True,
        )

    raise RuntimeError(
        f'Could not determine agent type in {current_dir}. '
        'Neither main.go nor main.py found.'
    )
