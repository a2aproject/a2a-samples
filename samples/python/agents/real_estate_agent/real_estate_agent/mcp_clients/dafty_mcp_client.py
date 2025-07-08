import os
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
import mcp.types as types

class DaftyMcpClient:
    def __init__(self):
        self.session: ClientSession | None = None
        self._transport_cm = None
        self._session_cm = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        if self.session:
            return

        url = os.environ.get("MCP_SERVER_URL")
        if not url:
            raise ValueError("MCP_SERVER_URL environment variable not set")

        self._transport_cm = sse_client(url)
        read_stream, write_stream = await self._transport_cm.__aenter__()

        try:
            self._session_cm = ClientSession(read_stream, write_stream)
            self.session = await self._session_cm.__aenter__()
            await self.session.initialize()
        except Exception:
            # If session setup fails, ensure transport is closed.
            await self._transport_cm.__aexit__(None, None, None)
            self._transport_cm = None
            raise

    async def search_rental_properties(self, args: dict) -> list[types.ContentBlock]:
        """A specific method for calling the 'search_rental_properties' tool."""
        return await self.call_tool("search_rental_properties", args)

    async def call_tool(self, tool_name: str, args: dict) -> list[types.ContentBlock]:
        if not self.session:
            raise RuntimeError("Client not connected")

        result = await self.session.call_tool(
            tool_name,
            arguments=args,
        )

        if result.isError:
            error_message = f"Tool call for '{tool_name}' failed."
            if result.content and isinstance(result.content[0], types.TextContent):
                try:
                    payload = json.loads(result.content[0].text)
                    # The payload's message is intended to be more user-friendly
                    error_message = payload.get("message", error_message)
                except json.JSONDecodeError:
                    # Fallback if the content is not JSON, append the raw text
                    error_message += f" Reason: {result.content[0].text}"
            raise RuntimeError(error_message)

        return result.content

    async def disconnect(self):
        if self._session_cm:
            await self._session_cm.__aexit__(None, None, None)
            self.session = None
            self._session_cm = None
        if self._transport_cm:
            await self._transport_cm.__aexit__(None, None, None)
            self._transport_cm = None