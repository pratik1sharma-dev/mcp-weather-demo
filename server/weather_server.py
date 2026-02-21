#!/usr/bin/env python3
"""
MCP Weather Server

Exposes weather-related tools through the Model Context Protocol.
Supports optional API key authentication for secure access.
"""

import asyncio
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from server.auth import AuthManager, validate_request

# Load environment variables
load_dotenv()

# OpenWeatherMap API configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Authentication configuration
auth_manager = AuthManager()

# Initialize MCP server
app = Server("weather-server")

# Store client API key (received during connection)
client_api_key = None


def get_weather_data(endpoint: str, params: dict) -> dict:
    """
    Fetch weather data from OpenWeatherMap API.

    Args:
        endpoint: API endpoint (e.g., 'weather', 'forecast')
        params: Query parameters

    Returns:
        JSON response from API
    """
    if not OPENWEATHER_API_KEY:
        return {"error": "OPENWEATHER_API_KEY not set in environment"}

    params["appid"] = OPENWEATHER_API_KEY
    params["units"] = "metric"  # Use Celsius

    try:
        response = requests.get(f"{OPENWEATHER_BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available weather tools.
    """
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'San Francisco' or 'London,UK')",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_forecast",
            description="Get 5-day weather forecast for a city (data points every 3 hours)",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'San Francisco' or 'Tokyo,JP')",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_weather_by_coordinates",
            description="Get current weather by geographic coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate",
                    },
                },
                "required": ["latitude", "longitude"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls from the client.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as TextContent
    """
    # Validate authentication
    is_valid, error_msg = validate_request(client_api_key, auth_manager)
    if not is_valid:
        return [TextContent(type="text", text=f"❌ Authentication Error: {error_msg}")]

    if name == "get_current_weather":
        city = arguments.get("city")
        data = get_weather_data("weather", {"q": city})

        if "error" in data:
            return [TextContent(type="text", text=f"Error: {data['error']}")]

        # Format the response
        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})

        result = f"""Current weather in {data.get('name', city)}:
- Condition: {weather.get('description', 'N/A').title()}
- Temperature: {main.get('temp', 'N/A')}°C (feels like {main.get('feels_like', 'N/A')}°C)
- Humidity: {main.get('humidity', 'N/A')}%
- Wind Speed: {wind.get('speed', 'N/A')} m/s
- Pressure: {main.get('pressure', 'N/A')} hPa"""

        return [TextContent(type="text", text=result)]

    elif name == "get_forecast":
        city = arguments.get("city")
        data = get_weather_data("forecast", {"q": city})

        if "error" in data:
            return [TextContent(type="text", text=f"Error: {data['error']}")]

        # Format forecast data (show daily summaries)
        forecasts = data.get("list", [])
        city_name = data.get("city", {}).get("name", city)

        result = f"5-day forecast for {city_name}:\n\n"

        # Group by day and show one forecast per day
        seen_dates = set()
        for item in forecasts:
            date = item.get("dt_txt", "").split()[0]
            if date and date not in seen_dates:
                seen_dates.add(date)
                weather = item.get("weather", [{}])[0]
                main = item.get("main", {})

                result += f"📅 {date}:\n"
                result += f"  - {weather.get('description', 'N/A').title()}\n"
                result += f"  - Temp: {main.get('temp', 'N/A')}°C\n"
                result += f"  - Humidity: {main.get('humidity', 'N/A')}%\n\n"

        return [TextContent(type="text", text=result)]

    elif name == "get_weather_by_coordinates":
        lat = arguments.get("latitude")
        lon = arguments.get("longitude")
        data = get_weather_data("weather", {"lat": lat, "lon": lon})

        if "error" in data:
            return [TextContent(type="text", text=f"Error: {data['error']}")]

        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})

        result = f"""Weather at ({lat}, {lon}):
- Location: {data.get('name', 'Unknown')}
- Condition: {weather.get('description', 'N/A').title()}
- Temperature: {main.get('temp', 'N/A')}°C
- Humidity: {main.get('humidity', 'N/A')}%"""

        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


def set_client_api_key(key: str):
    """Set the client API key from connection metadata."""
    global client_api_key
    client_api_key = key


# Custom initialization handler to receive API key
@app.initialize()
async def initialize(initialization_options=None):
    """
    Handle initialization with optional API key.

    Clients can pass API key through environment or connection metadata.
    """
    global client_api_key

    # Try to get API key from client environment (passed through)
    client_api_key = os.getenv("MCP_CLIENT_API_KEY")

    if auth_manager.is_enabled():
        if client_api_key:
            print("🔒 Authentication enabled - API key provided", file=sys.stderr)
        else:
            print("⚠️  Authentication enabled - No API key provided by client", file=sys.stderr)
    else:
        print("🔓 Authentication disabled - All requests allowed", file=sys.stderr)


async def main():
    """
    Run the MCP server.
    """
    if not OPENWEATHER_API_KEY:
        print("Error: OPENWEATHER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print("Starting MCP Weather Server...", file=sys.stderr)

    # Print authentication status
    if auth_manager.is_enabled():
        print(f"🔒 Authentication: ENABLED ({len(auth_manager.api_keys)} valid key(s))", file=sys.stderr)
    else:
        print("🔓 Authentication: DISABLED (set MCP_SERVER_API_KEYS to enable)", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
