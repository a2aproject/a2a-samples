
from google.adk.agents import LlmAgent
import logging
from typing import Dict
import google.cloud.logging
import google.auth

import urllib.request
# Imports from the google-auth library
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)
import os

load_dotenv()

weather_server_name = os.getenv("WEATHER_REMOTE_MCP_SERVER_NAME", "weather-remote-mcp-server")
project_number = os.getenv("PROJECT_NUMBER")
region = os.getenv("GOOGLE_CLOUD_LOCATION", 'us-central1')


def get_gcp_auth_headers(audience: str) -> Dict[str, str]:
    """
    Fetches a Google Cloud OIDC token for a target audience using ADC.

    This simplified function relies entirely on Application Default Credentials (ADC)
    and the google-auth library. The library automatically handles checking for
    local credentials, service accounts, or querying the metadata server,
    making a manual fallback unnecessary.

    Args:
        audience: The full URL/URI of the target service (e.g., your Cloud Run URL),
                  which is used as the audience for the OIDC token.

    Returns:
        A dictionary with the "Authorization" header, or an empty
        dictionary if auth fails or is skipped (e.g., no credentials).
    """
    try:
        # This single call is the canonical way to get an OIDC token using ADC.
        # It automatically finds credentials (local, SA, or metadata server).
        auth_req = google_auth_requests.Request()
        token = google_id_token.fetch_id_token(auth_req, audience)

        logging.info("Successfully fetched OIDC token via google.auth.")
        return {"Authorization": f"Bearer {token}"}

    except google_auth_exceptions.DefaultCredentialsError:
        # This is expected in local environments without ADC setup.
        logging.warning(
            "No Google Cloud credentials found (DefaultCredentialsError). "
            "Skipping OIDC token fetch. This is normal for local dev."
        )
        
    except Exception as e:
        # Any other error means ADC was likely found but token minting failed
        # (e.g., IAM permissions, wrong audience, metadata server unreachable).
        logging.critical(
            f"An unexpected error occurred fetching OIDC token for audience '{audience}': {e}",
            exc_info=True
        )

    # Return an empty dict if any exception occurred
    return {}


# def get_gcp_auth_headers(audience: str) -> Dict[str, str]:
#     """
#     Fetches a Google Cloud OIDC token for a target audience using ADC.
# 
#     This simplified function relies entirely on Application Default Credentials (ADC)
#     and the google-auth library. The library automatically handles checking for
#     local credentials, service accounts, or querying the metadata server,
#     making a manual fallback unnecessary.
# 
#     Args:
#         audience: The full URL/URI of the target service (e.g., your Cloud Run URL),
#                   which is used as the audience for the OIDC token.
# 
#     Returns:
#         A dictionary with the "Authorization" header, or an empty
#         dictionary if auth fails or is skipped (e.g., no credentials).
#     """
#     METADATA_SERVER_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience="
#     try:
#         # This single call is the canonical way to get an OIDC token using ADC.
#         # It automatically finds credentials (local, SA, or metadata server).
#         
#         creds, _ = google.auth.default()
#         logging.info("Successfully found Google Cloud credentials. Fetching OIDC token.")
#         url = f"{METADATA_SERVER_URL}{audience}"
#         req = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
#         with urllib.request.urlopen(req, timeout=5) as response:
#             token = response.read().decode("utf-8")
#         
# 
#         # auth_req = google_auth_requests.Request()
#         # token = google_id_token.fetch_id_token(auth_req, audience)
# 
#         logging.info("Successfully fetched OIDC token via google.auth.")
#         return {"Authorization": f"Bearer {token}"}
# 
#     except google_auth_exceptions.DefaultCredentialsError:
#         # This is expected in local environments without ADC setup.
#         logging.warning(
#             "No Google Cloud credentials found (DefaultCredentialsError). "
#             "Skipping OIDC token fetch. This is normal for local dev."
#         )
#         
#     except Exception as e:
#         # Any other error means ADC was likely found but token minting failed
#         # (e.g., IAM permissions, wrong audience, metadata server unreachable).
#         logging.critical(
#             f"An unexpected error occurred fetching OIDC token for audience '{audience}': {e}",
#             exc_info=True
#         )
# 
#     # Return an empty dict if any exception occurred
#     return {}


wea_url = f"https://{weather_server_name}-{project_number}.{region}.run.app/mcp/"
#wea_url = "https://weather-remote-mcp-server-496235138247.us-central1.run.app/mcp/"

wea_auth_headers = get_gcp_auth_headers(wea_url)

weather_server_params = StreamableHTTPConnectionParams(
    url=wea_url,
    headers=wea_auth_headers,
)


def create_weather_agent() -> LlmAgent:
    """Constructs the ADK agent."""
    return LlmAgent(
        model="gemini-2.5-flash",
        name="weather_agent",
        description="An agent that can help questions about weather",
        instruction=f"""You are a specialized weather forecast assistant. Your primary function is to utilize the provided tools to retrieve and relay weather information in response to user queries. You must rely exclusively on these tools for data and refrain from inventing information. Ensure that all responses include the detailed output from the tools used and are formatted in Markdown""",
        tools=[
            McpToolset(connection_params=weather_server_params)
        ],
    )

# weather_agent = create_weather_agent()
