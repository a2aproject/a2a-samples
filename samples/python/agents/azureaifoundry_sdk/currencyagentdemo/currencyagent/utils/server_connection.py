import asyncio
import json
import logging

from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


# Custom Exceptions
class MCPError(Exception):
    """Base exception for MCP-related errors."""


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""


class MCPToolNotFoundError(MCPError):
    """Raised when requested tool is not found on server."""


class MCPExecutionError(MCPError):
    """Raised when tool execution fails."""


class ConnectionState(Enum):
    """Enum for connection states."""

    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    RECONNECTING = 'reconnecting'
    ERROR = 'error'


@dataclass
class MCPConfig:
    """Configuration for MCP server connection."""

    server_url: str
    connection_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    health_check_interval: float = 30.0
    enable_auto_reconnect: bool = True
    max_concurrent_requests: int = 10
    request_timeout: float = 30.0

    def __post_init__(self):
        if not self.server_url:
            raise ValueError('server_url cannot be empty')
        if self.connection_timeout <= 0:
            raise ValueError('connection_timeout must be positive')
        if self.max_retries < 0:
            raise ValueError('max_retries cannot be negative')


@dataclass
class ToolInfo:
    """Information about an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    last_used: datetime | None = None
    usage_count: int = 0


@dataclass
class ConnectionStats:
    """Statistics about the connection."""

    connected_at: datetime | None = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    reconnection_count: int = 0
    last_error: str | None = None
    last_error_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def uptime(self) -> timedelta | None:
        """Calculate connection uptime."""
        if self.connected_at:
            return datetime.now() - self.connected_at
        return None


class ServerConnection:
    """Enhanced MCP server connection with robust error handling, connection pooling,
    health monitoring, and comprehensive statistics tracking.
    """

    def __init__(self, config: MCPConfig) -> None:
        """Initialize the ServerConnection with configuration.

        Args:
            config: MCPConfig instance with connection parameters
        """
        self.config = config
        self.session: ClientSession | None = None
        self._cleanup_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()
        self.exit_stack = AsyncExitStack()
        self._tools_cache: dict[str, ToolInfo] = {}
        self._connection_state = ConnectionState.DISCONNECTED
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self.stats = ConnectionStats()
        self._health_check_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return (
            self._connection_state == ConnectionState.CONNECTED
            and self.session is not None
        )

    @property
    def server_url(self) -> str:
        """Get server URL."""
        return self.config.server_url

    async def connect(self, timeout: float | None = None) -> bool:
        """Connect to the MCP server with enhanced error handling.

        Args:
            timeout: Connection timeout in seconds (overrides config)

        Returns:
            True if connection succeeded, False otherwise

        Raises:
            MCPConnectionError: On connection failure
        """
        timeout = timeout or self.config.connection_timeout

        async with self._connection_lock:
            if self.is_connected:
                logger.info('Already connected to MCP server')
                return True

            self._connection_state = ConnectionState.CONNECTING

            try:
                # Create connection with timeout
                connection_task = self._connect()
                await asyncio.wait_for(connection_task, timeout=timeout)

                self._connection_state = ConnectionState.CONNECTED
                self.stats.connected_at = datetime.now()
                self.stats.reconnection_count += 1

                # Start health check if enabled
                if self.config.health_check_interval > 0:
                    self._health_check_task = asyncio.create_task(
                        self._health_check_loop()
                    )

                logger.info(
                    f'Successfully connected to MCP server at {self.config.server_url}'
                )
                return True

            except TimeoutError as e:
                error_msg = f'Connection to {self.config.server_url} timed out after {timeout}s'
                logger.error(error_msg)
                self._handle_connection_error(error_msg)
                raise MCPConnectionError(error_msg) from e

            except Exception as e:
                error_msg = (
                    f'Failed to connect to {self.config.server_url}: {e}'
                )
                logger.error(error_msg)
                self._handle_connection_error(error_msg)
                raise MCPConnectionError(error_msg) from e

    async def _connect(self) -> None:
        """Internal method to establish server connection with proper resource tracking.

        Raises:
            MCPConnectionError: On connection failure
        """
        try:
            # Connect to the server using SSE
            read_write = await self.exit_stack.enter_async_context(
                sse_client(self.config.server_url)
            )
            read_stream, write_stream = read_write

            # Create and initialize session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            self.session = session

            logger.info(f'Connected to MCP server at {self.config.server_url}')

        except Exception as e:
            logger.error(f'Error connecting to MCP server: {e}')
            await self.cleanup()
            raise MCPConnectionError(f'Connection failed: {e}') from e

    async def disconnect(self) -> None:
        """Gracefully disconnect from the server."""
        logger.info('Disconnecting from MCP server...')
        self._shutdown_event.set()

        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Cancel reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        await self.cleanup()
        logger.info('Disconnected from MCP server')

    async def list_tools(self, force_refresh: bool = False) -> list[ToolInfo]:
        """List available tools from the MCP server with caching.

        Args:
            force_refresh: Whether to force refresh the tools cache

        Returns:
            List of ToolInfo objects

        Raises:
            MCPConnectionError: If not connected to server
        """
        if not self.is_connected:
            raise MCPConnectionError('Not connected to MCP server')

        if not self._tools_cache or force_refresh:
            try:
                tools_response = await self.session.list_tools()
                self._tools_cache = {
                    tool.name: ToolInfo(
                        name=tool.name,
                        description=tool.description,
                        input_schema=tool.inputSchema,
                    )
                    for tool in tools_response.tools
                }
                logger.info(
                    f'Cached {len(self._tools_cache)} tools from server'
                )
            except Exception as e:
                logger.error(f'Failed to list tools: {e}')
                raise MCPExecutionError(f'Failed to list tools: {e}') from e

        return list(self._tools_cache.values())

    async def get_tool_info(self, tool_name: str) -> ToolInfo | None:
        """Get information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolInfo object or None if tool not found
        """
        await self.list_tools()  # Ensure cache is populated
        return self._tools_cache.get(tool_name)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int | None = None,
        retry_delay: float | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute a tool on the MCP server with enhanced retry logic and concurrency control.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            retries: Number of retry attempts (overrides config)
            retry_delay: Base delay between retries (overrides config)
            timeout: Request timeout (overrides config)

        Returns:
            Tool execution result

        Raises:
            MCPConnectionError: If not connected to server
            MCPToolNotFoundError: If the tool doesn't exist
            MCPExecutionError: On tool execution failure after all retries
        """
        logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")

        if not self.is_connected:
            raise MCPConnectionError('Not connected to MCP server')

        # Use semaphore to limit concurrent requests
        async with self._semaphore:
            retries = (
                retries if retries is not None else self.config.max_retries
            )
            retry_delay = (
                retry_delay
                if retry_delay is not None
                else self.config.retry_delay
            )
            timeout = (
                timeout if timeout is not None else self.config.request_timeout
            )

            # Verify tool exists and update usage
            tool_info = await self.get_tool_info(tool_name)
            if not tool_info:
                error_msg = f"Tool '{tool_name}' not found on MCP server"
                self.stats.failed_requests += 1
                raise MCPToolNotFoundError(error_msg)

            # Update tool usage statistics
            tool_info.last_used = datetime.now()
            tool_info.usage_count += 1

            # Track request statistics
            self.stats.total_requests += 1

            # Implement retry with exponential backoff
            attempt = 0
            last_exception = None

            while attempt <= retries:
                try:
                    logger.debug(
                        f"Executing tool '{tool_name}' (attempt {attempt + 1}/{retries + 1})"
                    )

                    # Execute with timeout
                    execution_task = self.session.call_tool(
                        tool_name, arguments
                    )
                    result = await asyncio.wait_for(
                        execution_task, timeout=timeout
                    )

                    if result and result.content:
                        try:
                            response_data = json.loads(result.content[0].text)
                        except json.JSONDecodeError:
                            response_data = {'text': result.content[0].text}

                        self.stats.successful_requests += 1
                        logger.info(f"Successfully executed tool '{tool_name}'")
                        return response_data
                    response_data = {'error': 'No content received from tool'}
                    self.stats.successful_requests += (
                        1  # Still counts as successful call
                    )
                    return response_data

                except TimeoutError:
                    last_exception = MCPExecutionError(
                        f'Tool execution timed out after {timeout}s'
                    )
                except Exception as e:
                    last_exception = e

                attempt += 1
                if attempt <= retries:
                    # Exponential backoff with jitter
                    delay = min(
                        retry_delay * (2 ** (attempt - 1)),
                        self.config.max_retry_delay,
                    )
                    jitter = (
                        delay
                        * 0.1
                        * (0.5 - asyncio.get_event_loop().time() % 1)
                    )
                    actual_delay = delay + jitter

                    logger.warning(
                        f"Tool '{tool_name}' execution failed: {last_exception}. "
                        f'Retrying in {actual_delay:.1f}s...'
                    )
                    await asyncio.sleep(actual_delay)

            # All retries exhausted
            self.stats.failed_requests += 1
            self.stats.last_error = str(last_exception)
            self.stats.last_error_time = datetime.now()

            error_msg = f"Failed to execute tool '{tool_name}' after {retries + 1} attempts: {last_exception}"
            logger.error(error_msg)
            raise MCPExecutionError(error_msg) from last_exception

    async def health_check(self) -> bool:
        """Perform a health check on the connection.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.is_connected:
                return False

            # Simple health check - try to list tools
            await asyncio.wait_for(self.session.list_tools(), timeout=5.0)
            return True

        except Exception as e:
            logger.warning(f'Health check failed: {e}')
            return False

    async def _health_check_loop(self) -> None:
        """Background task to periodically check connection health."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if self._shutdown_event.is_set():
                    break

                if not await self.health_check():
                    logger.warning(
                        'Health check failed, attempting reconnection...'
                    )
                    if self.config.enable_auto_reconnect:
                        self._reconnect_task = asyncio.create_task(
                            self._auto_reconnect()
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in health check loop: {e}')

    async def _auto_reconnect(self) -> None:
        """Attempt to automatically reconnect to the server."""
        if self._connection_state == ConnectionState.RECONNECTING:
            return  # Already reconnecting

        self._connection_state = ConnectionState.RECONNECTING

        try:
            await self.cleanup()
            await asyncio.sleep(self.config.retry_delay)

            if await self.connect():
                logger.info('Auto-reconnection successful')
            else:
                logger.error('Auto-reconnection failed')
                self._connection_state = ConnectionState.ERROR

        except Exception as e:
            logger.error(f'Error during auto-reconnection: {e}')
            self._connection_state = ConnectionState.ERROR

    def _handle_connection_error(self, error_msg: str) -> None:
        """Handle connection errors by updating state and statistics.

        Args:
            error_msg: Error message to record
        """
        self._connection_state = ConnectionState.ERROR
        self.stats.last_error = error_msg
        self.stats.last_error_time = datetime.now()
        asyncio.create_task(self.cleanup())

    def get_stats(self) -> ConnectionStats:
        """Get connection statistics.

        Returns:
            ConnectionStats object with current statistics
        """
        return self.stats

    def get_tools_usage(self) -> dict[str, dict[str, Any]]:
        """Get tools usage statistics.

        Returns:
            Dictionary with tool usage information
        """
        return {
            tool_name: {
                'usage_count': tool_info.usage_count,
                'last_used': tool_info.last_used.isoformat()
                if tool_info.last_used
                else None,
                'description': tool_info.description,
            }
            for tool_name, tool_info in self._tools_cache.items()
        }

    async def cleanup(self) -> None:
        """Clean up all resources safely. Can be called multiple times."""
        async with self._cleanup_lock:
            logger.debug('Cleaning up server connection resources')
            try:
                self._connection_state = ConnectionState.DISCONNECTED
                await self.exit_stack.aclose()
                self.session = None
                # Don't clear tools cache to preserve usage statistics
                logger.info('Server connection resources cleaned up')
            except Exception as e:
                logger.warning(f'Error during resource cleanup: {e}')

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
