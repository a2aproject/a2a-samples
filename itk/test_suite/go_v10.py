import os
import subprocess

from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent


def spawn_agent(http_port: int, grpc_port: int) -> subprocess.Popen:
    """Spawns the Go v1.0 agent process.

    Args:
        http_port: The port for the HTTP/JSON-RPC interface.
        grpc_port: The port for the gRPC interface.

    Returns:
        subprocess.Popen: The spawned process object.
    """
    args = [  # noqa: S607
        'go',
        'run',
        'main.go',
        '--httpPort',
        str(http_port),
        '--grpcPort',
        str(grpc_port),
    ]
    cwd = _ROOT_DIR / 'agents/go/v10'

    log_level = os.environ.get('ITK_LOG_LEVEL', 'INFO')
    if log_level.upper() == 'DEBUG':
        logs_dir = _ROOT_DIR / 'logs'
        if not logs_dir.exists():
            raise RuntimeError(
                f"Logs directory '{logs_dir}' does not exist. Please create it or mount it."
            )
        stdout_file = open(logs_dir / 'agent_go_v10.log', 'w')

        p = subprocess.Popen(  # noqa: S603
            args,
            cwd=cwd,
            stdout=stdout_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return p
    else:
        return subprocess.Popen(  # noqa: S603
            args,
            cwd=cwd,
            stderr=subprocess.STDOUT,
            text=True,
        )
