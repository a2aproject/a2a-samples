import os
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

    log_level = os.environ.get('ITK_LOG_LEVEL', 'INFO')
    is_debug = log_level.upper() == 'DEBUG'

    if is_debug:
        logs_dir = _ROOT_DIR / 'logs'
        if not logs_dir.exists():
            raise RuntimeError(
                f"Logs directory '{logs_dir}' does not exist. Please create it or mount it."
            )
        stdout_file = open(logs_dir / 'agent_current.log', 'w')

    def popen_with_logs(args, cwd, stdout_override=None):
        if is_debug:
            p = subprocess.Popen(  # noqa: S603
                args,
                cwd=cwd,
                stdout=stdout_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return p
        else:
            kwargs = {
                'cwd': cwd,
                'stderr': subprocess.STDOUT,
                'text': True,
            }
            if stdout_override:
                kwargs['stdout'] = stdout_override
            return subprocess.Popen(args, **kwargs)  # noqa: S603

    if (current_dir / 'main.go').exists():
        # Go agent
        args = [  # noqa: S607
            'go',
            'run',
            'main.go',
            '--httpPort',
            str(http_port),
            '--grpcPort',
            str(grpc_port),
        ]
        return popen_with_logs(
            args, current_dir, stdout_override=subprocess.PIPE
        )

    if (current_dir / 'main.py').exists():
        # Python agent
        args = [  # noqa: S607
            'uv',
            'run',
            'main.py',
            '--httpPort',
            str(http_port),
            '--grpcPort',
            str(grpc_port),
        ]
        return popen_with_logs(args, current_dir)

    if (current_dir.parent / 'package.json').exists():
        # JS/TS agent
        args = [  # noqa: S607
            'npm',
            'run',
            'itk-agent',
            '--',
            '--httpPort',
            str(http_port),
            '--grpcPort',
            str(grpc_port),
        ]
        return popen_with_logs(args, current_dir)

    csproj_files = list(current_dir.glob('*.csproj'))
    if csproj_files:
        # Check local or system dotnet
        args = [  # noqa: S607
            'dotnet',
            'run',
            '--project',
            str(csproj_files[0]),
            '--',
            '--httpPort',
            str(http_port),
            '--grpcPort',
            str(grpc_port),
        ]
        return popen_with_logs(args, current_dir)

    raise RuntimeError(
        f'Could not determine agent type in {current_dir}. '
        'Neither main.go, main.py, package.json nor .csproj found.'
    )
