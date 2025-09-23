import asyncio
import json

from typing import Any

import httpx

from fastmcp import FastMCP
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim


# Initialize FastMCP server
mcp = FastMCP('weather MCP server')


# --- Configuration & Constants ---
BASE_URL = 'https://api.weather.gov'
USER_AGENT = 'weather-agent'
REQUEST_TIMEOUT = 20.0
GEOCODE_TIMEOUT = 10.0  # Timeout for geocoding requests

# --- Shared HTTP Client ---
http_client = httpx.AsyncClient(
    base_url=BASE_URL,
    headers={'User-Agent': USER_AGENT, 'Accept': 'application/geo+json'},
    timeout=REQUEST_TIMEOUT,
    follow_redirects=True,
)

# --- Geocoding Setup ---
geolocator = Nominatim(user_agent=USER_AGENT)


# --- Helper Functions ---
async def get_weather_response(endpoint: str) -> Any:
    """Generic helper to fetch and parse JSON from a weather.gov endpoint."""
    try:
        response = await http_client.get(endpoint)
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
        print(f"Weather API request failed for endpoint '{endpoint}': {e}")
        return None


def format_alert(feature: dict[str, Any]) -> str:
    """Format an alert feature into a readable string."""
    props = feature.get('properties', {})  # Safer access
    # Use .get() with default values for robustness
    return f"""
            Event: {props.get('event', 'Unknown Event')}
            Area: {props.get('areaDesc', 'N/A')}
            Severity: {props.get('severity', 'N/A')}
            Certainty: {props.get('certainty', 'N/A')}
            Urgency: {props.get('urgency', 'N/A')}
            Effective: {props.get('effective', 'N/A')}
            Expires: {props.get('expires', 'N/A')}
            Headline: {props.get('headline', 'N/A')}
            Description: {props.get('description', 'N/A')}
            Instruction: {props.get('instruction', 'N/A')}
            """


def format_forecast_period(period: dict[str, Any]) -> str:
    """Format a forecast period into a readable string."""
    return (
        f'{period.get("name", "N/A")}: {period.get("temperature")}°{period.get("temperatureUnit")}\n'
        f'Wind: {period.get("windSpeed")} {period.get("windDirection")}\n'
        f'Forecast: {period.get("shortForecast")}\n'
        f'{period.get("detailedForecast")}'
    )


# --- MCP Tools ---


@mcp.tool()
async def get_active_alerts_by_state(state: str) -> str:
    """Gets active weather alerts for a specific US state.

    Args:
        state: The two-letter US state code (e.g., CA, NY, TX). Case-insensitive.
    """
    # Input validation and normalization
    if not isinstance(state, str) or len(state) != 2 or not state.isalpha():
        return 'Invalid input. Please provide a two-letter US state code (e.g., CA).'
    state_code = state.upper()

    endpoint = f'/alerts/active/area/{state_code}'
    data = await get_weather_response(endpoint)

    if data is None:
        # Error occurred during request
        return f'Failed to retrieve weather alerts for {state_code}.'

    features = data.get('features')
    if not features:  # Handles both null and empty list
        return f'No active weather alerts found for {state_code}.'

    alerts = [format_alert(feature) for feature in features]
    return '\n---\n'.join(alerts)


# --- NEW: Internal Forecast Helper Function ---
async def _internal_get_forecast(latitude: float, longitude: float) -> str:
    """Internal helper to fetch and format forecast from coordinates."""
    # Input validation
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return 'Invalid latitude or longitude provided. Latitude must be between -90 and 90, Longitude between -180 and 180.'

    # NWS API requires latitude,longitude format with up to 4 decimal places
    point_endpoint = f'/points/{latitude:.4f},{longitude:.4f}'
    points_data = await get_weather_response(point_endpoint)

    if points_data is None or 'properties' not in points_data:
        return f'Unable to retrieve NWS gridpoint information for {latitude:.4f},{longitude:.4f}.'

    # Extract forecast URLs from the gridpoint data
    forecast_url = points_data['properties'].get('forecast')

    if not forecast_url:
        return f'Could not find the NWS forecast endpoint for {latitude:.4f},{longitude:.4f}.'

    # Make the request to the specific forecast URL
    forecast_data = None
    try:
        response = await http_client.get(forecast_url)
        response.raise_for_status()
        forecast_data = response.json()
    except httpx.RequestError:
        pass  # Error handled by returning None below
    except json.JSONDecodeError:
        pass  # Error handled by returning None below

    if forecast_data is None or 'properties' not in forecast_data:
        return 'Failed to retrieve detailed forecast data from NWS.'

    periods = forecast_data['properties'].get('periods')
    if not periods:
        return 'No forecast periods found for this location from NWS.'

    # Format the first 5 periods
    forecasts = [format_forecast_period(period) for period in periods[:5]]

    return '\n---\n'.join(forecasts)


# --- MODIFIED: get_forecast Tool (now a wrapper) ---
@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Gets the weather forecast for a given latitude and longitude."""
    return await _internal_get_forecast(latitude, longitude)


@mcp.tool()
async def get_forecast_by_city(city: str, state: str) -> str:
    """Gets the weather forecast for a given city and state.

    Args:
        city: The name of the city (e.g., "Los Angeles", "New York").
        state: The two-letter US state code (e.g., CA, NY). Case-insensitive.
    """
    # --- Input Validation ---
    if not city or not isinstance(city, str):
        return 'Invalid city name provided.'
    if (
        not state
        or not isinstance(state, str)
        or len(state) != 2
        or not state.isalpha()
    ):
        return 'Invalid state code. Please provide the two-letter US state abbreviation (e.g., CA).'

    city_name = city.strip()
    state_code = state.strip().upper()
    query = f'{city_name}, {state_code}, USA'

    # --- Geocoding (with asyncio.to_thread fix) ---
    location = None
    try:
        # Run the synchronous (blocking) geocode call in a separate thread
        location = await asyncio.to_thread(
            geolocator.geocode, query, exactly_one=True, timeout=GEOCODE_TIMEOUT
        )
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return f"Geocoding service error for '{query}': {e}"

    if location is None:
        return f"Could not find location for '{query}'. Please be more specific."

    # --- Forecast Fetching ---
    return await _internal_get_forecast(location.latitude, location.longitude)


# --- Add shutdown event to close client ---
@mcp.on_event('shutdown')
async def shutdown_event():
    """Gracefully close the httpx client."""
    await http_client.aclose()
    # print("HTTP client closed.") # Optional print statement if desired


if __name__ == '__main__':
    # mcp.run(transport="sse")
    asyncio.run(mcp.run_async(transport='streamable-http', host='0.0.0.0', port=8080))
