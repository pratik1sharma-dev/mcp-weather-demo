# MCP Weather Demo - Tutorial Guide

This guide explains the key concepts and architecture of the MCP (Model Context Protocol) using this weather demo.

## What is MCP?

**Model Context Protocol (MCP)** is an open protocol that standardizes how AI applications (like Claude) connect to data sources and tools. Think of it as a "USB for AI" - a universal standard for integrating external capabilities.

### Why MCP Matters

Before MCP:
- Every AI app needed custom integrations for each tool/API
- No standardization = lots of duplicate code
- Hard to share and reuse integrations

With MCP:
- ✅ One standard protocol
- ✅ Reusable server implementations
- ✅ Pluggable architecture
- ✅ Better security and control

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Your Application                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 MCP Client                           │   │
│  │  (client/weather_client.py)                          │   │
│  │                                                       │   │
│  │  • Connects to Claude API                            │   │
│  │  • Discovers available tools                         │   │
│  │  • Routes tool calls to MCP server                   │   │
│  └──────────────────┬───────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     │ MCP Protocol (stdio/JSON-RPC 2.0)
                     │
┌────────────────────┼────────────────────────────────────────┐
│  ┌─────────────────▼──────────────────────────────────┐    │
│  │              MCP Server                             │    │
│  │  (server/weather_server.py)                         │    │
│  │                                                      │    │
│  │  • Exposes tools (get_current_weather, etc.)        │    │
│  │  • Handles tool execution                           │    │
│  │  • Returns structured results                       │    │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│                     │ HTTPS                                  │
│                     │                                        │
│  ┌─────────────────▼──────────────────────────────────┐    │
│  │          OpenWeatherMap API                         │    │
│  │  (External weather data source)                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. MCP Server (`server/weather_server.py`)

The server exposes functionality through **tools**.

**Tools in this demo:**
- `get_current_weather`: Get current conditions for a city
- `get_forecast`: Get 5-day forecast
- `get_weather_by_coordinates`: Get weather by lat/lon

**Key code sections:**

```python
# Tool definition
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        ),
        # ... more tools
    ]

# Tool execution
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "get_current_weather":
        city = arguments.get("city")
        # Fetch and return weather data
```

### 2. MCP Client (`client/weather_client.py`)

The client connects to the server and orchestrates the interaction with Claude.

**Key responsibilities:**
1. Connect to MCP server via stdio
2. Discover available tools
3. Send user queries to Claude
4. Route Claude's tool calls to the MCP server
5. Return results back to Claude
6. Present final response to user

**The agentic loop:**

```python
while True:
    # 1. Claude decides what to do
    response = self.client.messages.create(
        model="claude-3-5-sonnet-20241022",
        tools=anthropic_tools,
        messages=messages,
    )

    # 2. If Claude wants to use a tool
    if response.stop_reason == "tool_use":
        # 3. Call the MCP server
        result = await self.session.call_tool(tool_name, tool_args)

        # 4. Send results back to Claude
        messages.append({"role": "user", "content": tool_results})
        # Loop continues...

    # 5. Claude provides final answer
    elif response.stop_reason == "end_turn":
        # Display response and exit loop
        break
```

## MCP Protocol Deep Dive

### Communication Transport

MCP uses **stdio** (standard input/output) for communication between client and server:
- Simple and universal
- Works across languages
- Easy to debug
- Secure (no network ports)

### Message Format

Messages follow **JSON-RPC 2.0** specification:

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_current_weather",
    "arguments": {"city": "San Francisco"}
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Current weather in San Francisco: Sunny, 18°C"
      }
    ]
  }
}
```

## Request Flow Example

Let's trace: **"What's the weather in Tokyo?"**

```
1. User asks: "What's the weather in Tokyo?"
   │
   ▼
2. Client sends query to Claude API
   │
   ▼
3. Claude analyzes query and decides to use tool
   Returns: {
     "tool_use": "get_current_weather",
     "arguments": {"city": "Tokyo"}
   }
   │
   ▼
4. Client calls MCP server via stdio
   Message: tools/call with {"city": "Tokyo"}
   │
   ▼
5. MCP server executes tool
   - Calls OpenWeatherMap API
   - Formats response
   - Returns to client
   │
   ▼
6. Client sends tool result back to Claude
   │
   ▼
7. Claude synthesizes natural language response
   "The current weather in Tokyo is partly cloudy
   with a temperature of 15°C..."
   │
   ▼
8. Client displays response to user
```

## MCP Capabilities (Beyond Tools)

While this demo focuses on **tools**, MCP supports other primitives:

### 1. Resources
Expose data that Claude can read (files, documents, database records)

```python
@app.list_resources()
async def list_resources():
    return [
        Resource(
            uri="weather://alerts/us",
            name="US Weather Alerts",
            mimeType="text/plain"
        )
    ]
```

### 2. Prompts
Reusable prompt templates with variables

```python
@app.list_prompts()
async def list_prompts():
    return [
        Prompt(
            name="daily_summary",
            description="Get daily weather summary",
            arguments=[
                PromptArgument(name="city", required=True)
            ]
        )
    ]
```

### 3. Sampling
Allow servers to request LLM completions through the client

## Best Practices

### 1. Tool Design
- ✅ Single responsibility per tool
- ✅ Clear descriptions for Claude
- ✅ Validate inputs
- ✅ Handle errors gracefully

### 2. Security
- ✅ Validate tool arguments
- ✅ Rate limit API calls
- ✅ Never expose sensitive credentials
- ✅ Use environment variables for API keys

### 3. Error Handling
- ✅ Return user-friendly error messages
- ✅ Log errors for debugging
- ✅ Handle network failures gracefully

## Extending This Demo

### Add More Tools
```python
Tool(
    name="get_air_quality",
    description="Get air quality index for a city",
    inputSchema={...}
)
```

### Add Resources
```python
# Expose current weather alerts as a resource
@app.list_resources()
async def list_resources():
    return [Resource(uri="weather://alerts", ...)]
```

### Add Authentication
```python
# Require API key for server access
@app.set_security()
async def check_auth(headers):
    # Verify API key
```

## Common Patterns

### Pattern 1: Multi-Step Queries
User: "Compare weather in Paris and Berlin"

→ Claude calls `get_current_weather` twice
→ Synthesizes comparison

### Pattern 2: Clarification
User: "What's the weather?"

→ Claude asks: "Which city?"
→ User: "Seattle"
→ Claude calls tool with clarified input

### Pattern 3: Tool Chaining
User: "Give me weather and forecast for NYC"

→ Claude calls `get_current_weather`
→ Claude calls `get_forecast`
→ Combines results

## Debugging Tips

### 1. Enable verbose logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Check stderr output
The client prints diagnostic info to stderr:
```
✅ Connected to MCP Weather Server
📦 Available tools: get_current_weather, get_forecast
🔧 Calling tool: get_current_weather
```

### 3. Test server independently
```bash
# Send test requests to server
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m server.weather_server
```

## Presentation Tips

1. **Start with the "why"**: Explain the problem MCP solves
2. **Show the flow**: Use diagrams to visualize client → Claude → server → API
3. **Live demo**: Run interactive mode and show real queries
4. **Show the code**: Walk through key parts (tool definition, tool calling)
5. **Discuss extensibility**: How easy it is to add new tools

## Resources

- MCP Specification: https://spec.modelcontextprotocol.io/
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Anthropic Documentation: https://docs.anthropic.com/
- OpenWeatherMap API: https://openweathermap.org/api

## Next Steps

After understanding this demo, you can:
1. Build your own MCP servers (database, CRM, custom APIs)
2. Integrate multiple MCP servers in one client
3. Explore MCP resources and prompts
4. Create production-ready MCP servers with authentication
