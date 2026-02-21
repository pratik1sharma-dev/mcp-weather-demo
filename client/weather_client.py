#!/usr/bin/env python3
"""
MCP Weather Client

Connects to the MCP Weather Server and uses Claude to process weather queries.
"""

import asyncio
import os
import sys
from contextlib import AsyncExitStack

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


class WeatherClient:
    """
    Client that connects to MCP Weather Server and uses Claude.
    """

    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
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

    async def process_query(self, query: str, tools: list):
        """
        Process a weather query using Claude and MCP tools.

        Args:
            query: User's weather query
            tools: Available MCP tools
        """
        print(f"🤔 Query: {query}\n")

        # Convert MCP tools to Anthropic tool format
        anthropic_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]

        # Initial message to Claude
        messages = [{"role": "user", "content": query}]

        # Agentic loop: Claude may need multiple turns to complete the task
        while True:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                tools=anthropic_tools,
                messages=messages,
            )

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Process tool calls
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_args = block.input

                        print(f"🔧 Calling tool: {tool_name}", file=sys.stderr)
                        print(f"   Arguments: {tool_args}", file=sys.stderr)

                        # Call the MCP server
                        result = await self.session.call_tool(tool_name, tool_args)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content,
                        })

                # Add assistant response and tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Claude has finished, extract the final response
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text

                print(f"🤖 Claude's Response:\n{final_response}\n")
                break

            else:
                print(f"⚠️  Unexpected stop reason: {response.stop_reason}", file=sys.stderr)
                break

    async def run_interactive(self):
        """
        Run the client in interactive mode.
        """
        tools = await self.connect_to_server()

        print("=" * 60)
        print("🌤️  MCP Weather Demo - Interactive Mode")
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
        print("🌤️  MCP Weather Demo - Automated Demo")
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
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
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
