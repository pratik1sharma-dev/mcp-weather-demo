#!/usr/bin/env python3
"""
MCP Weather Client

Connects to the MCP Weather Server and uses Google Gemini to process weather queries.
"""

import asyncio
import os
import sys
import json
from contextlib import AsyncExitStack

import google.generativeai as genai
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class WeatherClient:
    """
    Client that connects to MCP Weather Server and uses Gemini.
    """

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',  # Free tier model
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'max_output_tokens': 8192,
            }
        )
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self):
        """
        Connect to the MCP Weather Server via stdio.
        """
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "server.weather_server"],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print(f"\n✅ Connected to MCP Weather Server", file=sys.stderr)
        print(f"📦 Available tools: {', '.join(tool.name for tool in tools)}\n", file=sys.stderr)

        return tools

    def convert_to_gemini_tools(self, mcp_tools):
        """
        Convert MCP tools to Gemini function declarations.

        Args:
            mcp_tools: List of MCP Tool objects

        Returns:
            List of Gemini function declarations
        """
        gemini_tools = []

        for tool in mcp_tools:
            function_declaration = genai.protos.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        prop_name: genai.protos.Schema(
                            type=genai.protos.Type.STRING if prop_def.get('type') == 'string'
                                 else genai.protos.Type.NUMBER if prop_def.get('type') == 'number'
                                 else genai.protos.Type.STRING,
                            description=prop_def.get('description', '')
                        )
                        for prop_name, prop_def in tool.inputSchema.get('properties', {}).items()
                    },
                    required=tool.inputSchema.get('required', [])
                )
            )
            gemini_tools.append(function_declaration)

        return gemini_tools

    async def process_query(self, query: str, tools: list):
        """
        Process a weather query using Gemini and MCP tools.

        Args:
            query: User's weather query
            tools: Available MCP tools
        """
        print(f"🤔 Query: {query}\n")

        # Convert MCP tools to Gemini format
        gemini_tools = self.convert_to_gemini_tools(tools)

        # Create a model with tools
        model_with_tools = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=gemini_tools
        )

        # Start chat
        chat = model_with_tools.start_chat(enable_automatic_function_calling=False)

        # Send initial message
        response = chat.send_message(query)

        # Agentic loop: Handle function calls
        max_iterations = 10
        for iteration in range(max_iterations):
            # Check if Gemini wants to call functions
            if response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                # If there's a function call
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)

                    print(f"🔧 Calling tool: {function_name}", file=sys.stderr)
                    print(f"   Arguments: {function_args}", file=sys.stderr)

                    # Call the MCP server
                    result = await self.session.call_tool(function_name, function_args)

                    # Extract text from result
                    result_text = ""
                    for content in result.content:
                        if hasattr(content, 'text'):
                            result_text += content.text

                    # Send function response back to Gemini
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=function_name,
                                        response={'result': result_text}
                                    )
                                )
                            ]
                        )
                    )

                # If there's text (final response)
                elif hasattr(part, 'text') and part.text:
                    print(f"🤖 Gemini's Response:\n{part.text}\n")
                    break
            else:
                # Empty response, shouldn't happen
                print("⚠️  Received empty response from Gemini", file=sys.stderr)
                break
        else:
            print("⚠️  Max iterations reached", file=sys.stderr)

    async def run_interactive(self):
        """
        Run the client in interactive mode.
        """
        tools = await self.connect_to_server()

        print("=" * 60)
        print("🌤️  MCP Weather Demo - Interactive Mode (Powered by Gemini)")
        print("=" * 60)
        print("\nAsk me about the weather! Examples:")
        print("  - What's the weather like in San Francisco?")
        print("  - Give me a 5-day forecast for Tokyo")
        print("  - Compare weather in London and Paris")
        print("\nType 'quit' or 'exit' to stop.\n")

        while True:
            try:
                query = input("You: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break

                if not query:
                    continue

                await self.process_query(query, tools)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n", file=sys.stderr)

    async def run_demo(self):
        """
        Run a demo with pre-defined queries.
        """
        tools = await self.connect_to_server()

        demo_queries = [
            "What's the current weather in San Francisco?",
            "Give me a 5-day forecast for Tokyo",
            "What's the weather at coordinates 51.5074, -0.1278?",  # London
        ]

        print("=" * 60)
        print("🌤️  MCP Weather Demo - Automated Demo (Powered by Gemini)")
        print("=" * 60)
        print()

        for query in demo_queries:
            await self.process_query(query, tools)
            print("-" * 60)
            print()
            await asyncio.sleep(1)

    async def cleanup(self):
        """
        Clean up resources.
        """
        await self.exit_stack.aclose()


async def main():
    """
    Main entry point.
    """
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        print("\nGet your FREE API key from: https://makersuite.google.com/app/apikey", file=sys.stderr)
        sys.exit(1)

    client = WeatherClient()

    try:
        # Check if running in demo mode
        if len(sys.argv) > 1 and sys.argv[1] == "--demo":
            await client.run_demo()
        else:
            await client.run_interactive()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
