# MCP Weather Demo

A demonstration of the Model Context Protocol (MCP) using a weather service as the use case.

## Overview

This demo showcases how MCP enables AI models to interact with external services through a standardized protocol. It consists of:

- **MCP Server**: Exposes weather-related tools (current weather, forecasts, alerts)
- **Client Application**: Connects to the server and uses AI (configurable: Gemini or Claude) to answer weather queries

## Prerequisites

- Python 3.10+
- OpenWeatherMap API key (FREE: https://openweathermap.org/api)
- **Choose your AI provider:**
  - **Google Gemini** (Recommended for demos - FREE tier) ⭐
  - **Anthropic Claude** (Paid, but $5 free credits for new accounts)

## Quick Start

1. **Clone and setup**:
```bash
cd mcp-weather-demo
pip install -r requirements.txt
```

2. **Get API keys**:
   - OpenWeatherMap: https://openweathermap.org/api (FREE)
   - **Option A (Recommended)**: Google Gemini: https://makersuite.google.com/app/apikey (FREE) ⭐
   - **Option B**: Anthropic Claude: https://console.anthropic.com/ ($5 free credits)

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and choose your AI provider:

# For Gemini (FREE, recommended for demos):
AI_PROVIDER=gemini
OPENWEATHER_API_KEY=your_key_here
GEMINI_API_KEY=your_gemini_key_here

# OR for Claude (paid):
AI_PROVIDER=anthropic
OPENWEATHER_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
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
- Uses your configured AI provider (Gemini or Claude)
- Calls the appropriate weather tools
- Presents natural language responses

You can switch providers by changing `AI_PROVIDER` in your `.env` file.

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

1. **Client** sends a user query to AI (Gemini or Claude)
2. **AI** decides which weather tools to call based on the query
3. **Client** forwards tool calls to the **MCP Server** via MCP protocol
4. **MCP Server** fetches weather data from OpenWeatherMap API
5. **Client** sends tool results back to AI
6. **AI** synthesizes a natural language response

## AI Provider Comparison

| Feature | Gemini (Default) | Claude |
|---------|------------------|--------|
| **Cost** | ⭐ FREE (generous limits) | Paid ($5 free credits) |
| **Rate Limits** | 15/min, 1500/day | Based on plan |
| **Function Calling** | ✅ Excellent | ✅ Excellent |
| **Setup** | Sign in with Google | Credit card required |
| **Best For** | Demos, tutorials, testing | Production apps |

**Recommendation**: Start with **Gemini** (free) for demos and learning!

## MCP Concepts Demonstrated

- **Tools**: Weather tools exposed by the server (get_current_weather, get_forecast, etc.)
- **Server**: Standardized way to expose functionality to AI models
- **Client Integration**: How to connect MCP servers with AI models (Gemini or Claude)
- **Protocol**: JSON-RPC 2.0 communication over stdio
- **Function Calling**: How AI models invoke tools through MCP
- **Authentication**: Optional API key-based authentication for secure access

## 🔒 Security (Optional)

The server supports **API key authentication** to control access. This is useful for production deployments.

**Quick setup:**
```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env:
MCP_SERVER_API_KEYS=your_generated_key
MCP_CLIENT_API_KEY=your_generated_key
```

For detailed instructions, see [AUTHENTICATION.md](AUTHENTICATION.md).

**Note:** Authentication is **disabled by default** for easy local development. Leave `MCP_SERVER_API_KEYS` empty to skip authentication.

## Documentation

- **[README.md](README.md)** - Quick start guide (you are here)
- **[TUTORIAL.md](TUTORIAL.md)** - Deep dive into MCP concepts
- **[AUTHENTICATION.md](AUTHENTICATION.md)** - Security and API key setup
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

## License

MIT
