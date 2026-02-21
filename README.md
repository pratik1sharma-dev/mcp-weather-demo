# MCP Weather Demo

A demonstration of the Model Context Protocol (MCP) using a weather service as the use case.

## Overview

This demo showcases how MCP enables AI models to interact with external services through a standardized protocol. It consists of:

- **MCP Server**: Exposes weather-related tools (current weather, forecasts, alerts)
- **Client Application**: Connects to the server and uses Google Gemini (FREE tier!) to answer weather queries

## Prerequisites

- Python 3.10+
- OpenWeatherMap API key (FREE tier: https://openweathermap.org/api)
- Google Gemini API key (FREE tier: https://makersuite.google.com/app/apikey) ⭐

## Quick Start

1. **Clone and setup**:
```bash
cd mcp-weather-demo
pip install -r requirements.txt
```

2. **Get FREE API keys**:
   - OpenWeatherMap: https://openweathermap.org/api
   - Google Gemini: https://makersuite.google.com/app/apikey ⭐ **Generous free tier!**

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# OPENWEATHER_API_KEY=your_key_here
# GEMINI_API_KEY=your_key_here
```

4. **Run the demo**:
```bash
# Option 1: Interactive mode (recommended for first time)
python -m client.weather_client

# Option 2: Automated demo mode
python -m client.weather_client --demo
```

## Project Structure

```
mcp-weather-demo/
├── server/
│   ├── __init__.py
│   └── weather_server.py    # MCP server implementation
├── client/
│   ├── __init__.py
│   └── weather_client.py    # Client that uses Claude + MCP
├── requirements.txt
├── .env.example
└── README.md
```

## Usage

### Interactive Mode (Default)

```bash
python -m client.weather_client
```

This starts an interactive session where you can ask weather questions. The client automatically:
- Connects to the MCP server (no separate terminal needed!)
- Uses Google Gemini to understand your queries
- Calls the appropriate weather tools
- Presents natural language responses

### Demo Mode

```bash
python -m client.weather_client --demo
```

Runs a pre-defined set of queries to showcase the capabilities.

### Example Queries

Try asking:
- "What's the weather like in San Francisco?"
- "Give me a 5-day forecast for Tokyo"
- "What's the weather at coordinates 51.5074, -0.1278?"
- "Compare the weather in London and Paris"
- "Is it warmer in New York or Los Angeles right now?"

## How It Works

1. **Client** sends a user query to Google Gemini
2. **Gemini** decides which weather tools to call based on the query
3. **Client** forwards tool calls to the **MCP Server** via MCP protocol
4. **MCP Server** fetches weather data from OpenWeatherMap API
5. **Client** sends tool results back to Gemini
6. **Gemini** synthesizes a natural language response

## Why Gemini?

✅ **Generous FREE tier** - 15 requests per minute, 1500 requests per day
✅ **Function calling support** - Perfect for MCP tools
✅ **Fast and reliable** - Great for demos and tutorials
✅ **No credit card required** - Just sign in with Google

## MCP Concepts Demonstrated

- **Tools**: Weather tools exposed by the server (get_current_weather, get_forecast, etc.)
- **Server**: Standardized way to expose functionality to AI models
- **Client Integration**: How to connect MCP servers with AI models (Gemini in this case)
- **Protocol**: JSON-RPC 2.0 communication over stdio
- **Function Calling**: How AI models invoke tools through MCP

## License

MIT
