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

The client connects to the server and orchestrates the interaction with AI models.

**Configurable Architecture:**
The client supports multiple AI providers through an abstract `AIProvider` interface:
- `GeminiProvider` - Google Gemini (FREE tier)
- `AnthropicProvider` - Anthropic Claude (paid)

Switch providers by setting `AI_PROVIDER=gemini` or `AI_PROVIDER=anthropic` in `.env`.

**Key responsibilities:**
1. Connect to MCP server via stdio
2. Discover available tools
3. Send user queries to AI provider
4. Route AI's tool calls to the MCP server
5. Return results back to AI
6. Present final response to user

**The agentic loop:**

```python
# Start chat with Gemini
chat = model_with_tools.start_chat()
response = chat.send_message(query)

for iteration in range(max_iterations):
    # 1. Check if Gemini wants to call a function
    if hasattr(part, 'function_call') and part.function_call:
        function_call = part.function_call

        # 2. Call the MCP server
        result = await self.session.call_tool(
            function_call.name,
            dict(function_call.args)
        )

        # 3. Send results back to Gemini
        response = chat.send_message(
            function_response=FunctionResponse(
                name=function_call.name,
                response={'result': result_text}
            )
        )
        # Loop continues...

    # 4. Gemini provides final answer
    elif hasattr(part, 'text') and part.text:
        print(part.text)
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
2. Client sends query to Gemini API
   │
   ▼
3. Gemini analyzes query and decides to use tool
   Returns: {
     "function_call": {
       "name": "get_current_weather",
       "args": {"city": "Tokyo"}
     }
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
6. Client sends tool result back to Gemini
   │
   ▼
7. Gemini synthesizes natural language response
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

### Add More AI Providers
The client uses a plugin architecture. To add a new provider:

```python
class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_name(self) -> str:
        return "OpenAI GPT-4"

    async def process_query(self, query, tools, session):
        # Implement OpenAI function calling
        ...
```

Then update `WeatherClient._create_provider()` to support `AI_PROVIDER=openai`.

### Add Resources
```python
# Expose current weather alerts as a resource
@app.list_resources()
async def list_resources():
    return [Resource(uri="weather://alerts", ...)]
```

### Authentication (Already Implemented!)

This demo includes **API key authentication**:

```python
# Server: Validate API key before processing
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    is_valid, error_msg = validate_request(client_api_key, auth_manager)
    if not is_valid:
        return [TextContent(type="text", text=f"❌ {error_msg}")]
    # ... process tool call
```

**Enable authentication:**
```bash
# Generate key
python generate_api_key.py

# Add to .env
MCP_SERVER_API_KEYS=your_key_here
MCP_CLIENT_API_KEY=your_key_here
```

See [AUTHENTICATION.md](AUTHENTICATION.md) for full guide.

## Common Patterns

### Pattern 1: Multi-Step Queries
User: "Compare weather in Paris and Berlin"

→ Gemini calls `get_current_weather` twice
→ Synthesizes comparison

### Pattern 2: Clarification
User: "What's the weather?"

→ Gemini asks: "Which city?"
→ User: "Seattle"
→ Gemini calls tool with clarified input

### Pattern 3: Tool Chaining
User: "Give me weather and forecast for NYC"

→ Gemini calls `get_current_weather`
→ Gemini calls `get_forecast`
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
2. **Show the flow**: Use diagrams to visualize client → Gemini → server → API
3. **Live demo**: Run interactive mode and show real queries
4. **Show the code**: Walk through key parts (tool definition, function calling)
5. **Discuss extensibility**: How easy it is to add new tools
6. **Highlight free tier**: Emphasize that this demo costs $0 to run!

## Resources

- MCP Specification: https://spec.modelcontextprotocol.io/
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Google Gemini API: https://ai.google.dev/
- Gemini API Key (FREE): https://makersuite.google.com/app/apikey
- OpenWeatherMap API: https://openweathermap.org/api

## Next Steps

After understanding this demo, you can:
1. Build your own MCP servers (database, CRM, custom APIs)
2. Integrate multiple MCP servers in one client
3. Explore MCP resources and prompts
4. Create production-ready MCP servers with authentication
