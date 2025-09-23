import asyncio

from fastmcp import Client

async def test_server():
    # Test the MCP server using streamable-http transport.
    # Use "/sse" endpoint if using sse transport.
    async with Client("http://localhost:8080/mcp") as client:
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f">>> 🛠️  Tool found: {tool.name}")
        # Call add tool
        result = await client.call_tool("get_forecast_by_city", {"city": "New York", "state": "NY"})
        print(f"<<< ✅ Result: {result[0].text}")
       

if __name__ == "__main__":
    asyncio.run(test_server())