# Import libraries
import uvicorn
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import Response

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

@mcp.tool()
def get_articles_by_tag(tag: str) -> list:
    """
    Fetch articles by a specific tag from DevTo.
    
    Args:
        tag (str): The tag to filter articles by.

    Returns:
        list: A list of articles with the specified tag.
    """

    return devto_service.get_articles_by_tag(tag=tag)

@mcp.tool()
def get_articles_by_tags(tags: list) -> list:
    """
    Fetch articles by multiple tags from DevTo.
    
    Args:
        tags (list): A list of tags to filter articles by.

    Returns:
        list: A list of articles with the specified tags.
    """

    return devto_service.get_articles_by_tags(tags=tags)

@mcp.tool()
def get_article_content(article_id: int) -> dict:
    """
    Fetch the content of a specific article from DevTo.
    
    Args:
        article_id (int): The ID of the article to fetch.

    Returns:
        dict: The content of the specified article.
    """

    return devto_service.get_article_content(article_id=article_id)

@mcp.tool()
def get_user() -> dict:
    """
    Fetch the current user's information from DevTo.
    
    Returns:
        dict: The current user's information.
    """

    return devto_service.get_user()

@mcp.tool()
def get_user_articles() -> list:
    """
    Fetch all articles authored by the current user from DevTo.
    
    Returns:
        list: A list of articles authored by the current user.
    """

    return devto_service.get_user_articles()

@mcp.tool()
def get_user_published_articles() -> list:
    """
    Fetch all published articles authored by the current user from DevTo.
    
    Returns:
        list: A list of published articles authored by the current user.
    """

    return devto_service.get_user_published_articles()

@mcp.tool()
def post_article(title: str, body: str, tags: list) -> dict:
    """
    Post a new article to DevTo.
    
    Args:
        title (str): The title of the article.
        body (str): The body content of the article in Markdown format.
        tags (list): A list of tags for the article.

    Returns:
        dict: The response from the DevTo API after posting the article.
    """

    return devto_service.post_article(title=title, body=body, tags=tags)

@mcp.tool()
def get_user_followers() -> list:
    """
    Fetch the followers of the current user from DevTo.
    
    Returns:
        list: A list of followers of the current user.
    """

    return devto_service.get_user_followers()

@mcp.tool()
def get_user_reading_list() -> list:
    """
    Fetch the current user's reading list from DevTo.
    
    Returns:
        list: A list of articles in the user's reading list.
    """

    return devto_service.get_user_reading_list()

@mcp.tool()
def get_article_comments(article_id: int) -> list:
    """
    Fetch comments for a specific article from DevTo.
    
    Args:
        article_id (int): The ID of the article to fetch comments for.

    Returns:
        list: A list of comments for the specified article.
    """

    return devto_service.get_article_comments(article_id=article_id)


def create_starlette_app(
    mcp_server: Server = mcp,
    *,
    debug: bool = False,
) -> Starlette:
    """
    Create a Starlette application with the MCP server.
    
    Args:
        mcp (Server): The MCP server instance.
        debug (bool): Whether to run the application in debug mode.

    Returns:
        Starlette: The Starlette application instance.
    """

    sse = SseServerTransport('/messages/')

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )
        return Response(status_code=204)

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message)
        ]
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437
    app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(app, host='localhost', port=8000)
