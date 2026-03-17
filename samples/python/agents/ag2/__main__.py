"""Entry point for the AG2 A2A Python Reviewer agent."""

import click
import uvicorn

from a2a_python_reviewer import build_server


@click.command()
@click.option('--host', default='localhost', help='Host to bind to.')
@click.option('--port', default=10012, help='Port to bind to.')
def main(host: str, port: int) -> None:
    """Run the AG2 A2A Python Reviewer agent."""
    server = build_server(host, port)
    uvicorn.run(server, host=host, port=port)


if __name__ == '__main__':
    main()
