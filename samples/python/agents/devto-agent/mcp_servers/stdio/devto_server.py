# Import libraries
import uvicorn
from mcp.server.fastmcp import FastMCP

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from services.devto_service import DevToService

mcp = FastMCP("DevTo MCP Server")

devto_service = DevToService()

@mcp.tool()
def get_articles(page: int = 1, per_page: int = 30) -> list:
    """
    Fetch articles from DevTo.
    
    Args:
        page (int): The page number to fetch.
        per_page (int): The number of articles per page.

    Returns:
        list: A list of articles from DevTo.
    """

    return devto_service.get_articles(page=page, per_page=per_page)


if __name__ == "__main__":
    mcp.run(transport='stdio')