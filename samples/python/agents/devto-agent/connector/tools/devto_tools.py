# Import libraries
from termcolor import colored
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

async def get_devto_tools() -> tuple:
    """
    Retrieves the DevTo tools for agent.

    Returns:
        tuple: A tuple containing the DevTo toolset and exit stack.
    """
    
    print(colored("Attempting to connect with DevTo MCP server for blogs info...", "yellow"))
    
    server_parameters = SseServerParams(
        url="http://localhost:8000/sse/",
    )
    
    tools, exit_stack = await MCPToolset.from_server(connection_params=server_parameters)
    print(colored("MCP Toolset created successfully.", "green"))
    return tools, exit_stack