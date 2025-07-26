# Create global connection manager
from typing import Any

from .server_connection import ConnectionStats, MCPConfig, ServerConnection


class MCPToolManager:
    """Manager for MCP tools with connection pooling and caching."""

    def __init__(self, server_url: str, config: MCPConfig | None = None):
        self.config = config or MCPConfig(server_url=server_url)
        self._connection: ServerConnection | None = None
        self._tools_cache: dict[str, dict[str, Any]] = {}
        self._functions_dict: dict[str, callable] = {}

    async def initialize(self) -> None:
        """Initialize the connection and load tools."""
        if self._connection is None:
            self._connection = ServerConnection(self.config)
            await self._connection.connect()

            # Load and cache tools
            tools = await self._connection.list_tools()
            self._tools_cache = {
                tool.name: {
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': tool.input_schema,
                }
                for tool in tools
            }

            # Create function wrappers
            self._functions_dict = {
                tool_name: self._make_tool_func(tool_name)
                for tool_name in self._tools_cache.keys()
            }

    def _make_tool_func(self, tool_name: str):
        """Create a function wrapper for an MCP tool using the shared connection."""

        async def async_tool_func(**kwargs):
            if not self._connection or not self._connection.is_connected:
                await self.initialize()

            try:
                result = await self._connection.execute_tool(tool_name, kwargs)
                return result
            except Exception as e:
                # logger.error(f"Error executing tool '{tool_name}': {e}")
                return {'error': str(e)}

        # Return the async function directly - we'll handle the event loop in the caller
        async_tool_func.__name__ = tool_name
        async_tool_func.__doc__ = self._tools_cache.get(tool_name, {}).get(
            'description', f'MCP tool: {tool_name}'
        )
        return async_tool_func

    def get_tools(self) -> dict[str, dict[str, Any]]:
        """Get cached tools information."""
        return self._tools_cache.copy()

    def get_functions(self) -> dict[str, callable]:
        """Get all tool functions."""
        return self._functions_dict.copy()

    def get_stats(self) -> ConnectionStats | None:
        """Get connection statistics."""
        if self._connection:
            return self._connection.get_stats()
        return None

    def get_tools_usage(self) -> dict[str, dict[str, Any]]:
        """Get tools usage statistics."""
        if self._connection:
            return self._connection.get_tools_usage()
        return {}

    async def close(self) -> None:
        """Close the connection."""
        if self._connection:
            await self._connection.disconnect()
            self._connection = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
