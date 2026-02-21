#!/usr/bin/env python3
"""
MCP Weather Client

Connects to the MCP Weather Server and uses AI (Gemini or Anthropic) to process weather queries.
Supports multiple AI providers through a configurable interface.
"""

import asyncio
import os
import sys
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def process_query(self, query: str, tools: list, session: ClientSession) -> str:
        """
        Process a query using the AI provider.

        Args:
            query: User's question
            tools: Available MCP tools
            session: MCP client session for tool calls

        Returns:
            AI's response as a string
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name."""
        pass


class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self):
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            )

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")

        self.genai.configure(api_key=GEMINI_API_KEY)

    def get_name(self) -> str:
        return "Google Gemini (FREE)"

    def _convert_to_gemini_tools(self, mcp_tools):
        """Convert MCP tools to Gemini function declarations."""
        gemini_tools = []

        for tool in mcp_tools:
            function_declaration = self.genai.protos.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=self.genai.protos.Schema(
                    type=self.genai.protos.Type.OBJECT,
                    properties={
                        prop_name: self.genai.protos.Schema(
                            type=self.genai.protos.Type.STRING
                            if prop_def.get("type") == "string"
                            else self.genai.protos.Type.NUMBER
                            if prop_def.get("type") == "number"
                            else self.genai.protos.Type.STRING,
                            description=prop_def.get("description", ""),
                        )
                        for prop_name, prop_def in tool.inputSchema.get(
                            "properties", {}
                        ).items()
                    },
                    required=tool.inputSchema.get("required", []),
                )
            )
            gemini_tools.append(function_declaration)

        return gemini_tools

    async def process_query(
        self, query: str, tools: list, session: ClientSession
    ) -> str:
        """Process query using Gemini."""
        gemini_tools = self._convert_to_gemini_tools(tools)

        model_with_tools = self.genai.GenerativeModel(
            model_name="gemini-1.5-flash", tools=gemini_tools
        )

        chat = model_with_tools.start_chat(enable_automatic_function_calling=False)
        response = chat.send_message(query)

        max_iterations = 10
        for iteration in range(max_iterations):
            if response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                if hasattr(part, "function_call") and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)

                    print(f"🔧 Calling tool: {function_name}", file=sys.stderr)
                    print(f"   Arguments: {function_args}", file=sys.stderr)

                    result = await session.call_tool(function_name, function_args)

                    result_text = ""
                    for content in result.content:
                        if hasattr(content, "text"):
                            result_text += content.text

                    response = chat.send_message(
                        self.genai.protos.Content(
                            parts=[
                                self.genai.protos.Part(
                                    function_response=self.genai.protos.FunctionResponse(
                                        name=function_name,
                                        response={"result": result_text},
                                    )
                                )
                            ]
                        )
                    )

                elif hasattr(part, "text") and part.text:
                    return part.text
            else:
                return "⚠️ Received empty response"

        return "⚠️ Max iterations reached"


class AnthropicProvider(AIProvider):
    """Anthropic Claude AI provider."""

    def __init__(self):
        try:
            from anthropic import Anthropic
            self.Anthropic = Anthropic
        except ImportError:
            raise ImportError(
                "anthropic not installed. Run: pip install anthropic"
            )

        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        self.client = self.Anthropic(api_key=ANTHROPIC_API_KEY)

    def get_name(self) -> str:
        return "Anthropic Claude"

    def _convert_to_anthropic_tools(self, mcp_tools):
        """Convert MCP tools to Anthropic tool format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in mcp_tools
        ]

    async def process_query(
        self, query: str, tools: list, session: ClientSession
    ) -> str:
        """Process query using Claude."""
        anthropic_tools = self._convert_to_anthropic_tools(tools)
        messages = [{"role": "user", "content": query}]

        max_iterations = 10
        for iteration in range(max_iterations):
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                tools=anthropic_tools,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_args = block.input

                        print(f"🔧 Calling tool: {tool_name}", file=sys.stderr)
                        print(f"   Arguments: {tool_args}", file=sys.stderr)

                        result = await session.call_tool(tool_name, tool_args)

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result.content,
                            }
                        )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text
                return final_response

            else:
                return f"⚠️ Unexpected stop reason: {response.stop_reason}"

        return "⚠️ Max iterations reached"


class WeatherClient:
    """
    Client that connects to MCP Weather Server and uses AI.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        if provider:
            self.provider = provider
        else:
            # Auto-select provider based on environment
            self.provider = self._create_provider()

        self.session = None
        self.exit_stack = AsyncExitStack()

    def _create_provider(self) -> AIProvider:
        """Create AI provider based on configuration."""
        if AI_PROVIDER == "gemini":
            return GeminiProvider()
        elif AI_PROVIDER == "anthropic":
            return AnthropicProvider()
        else:
            raise ValueError(
                f"Unknown AI_PROVIDER: {AI_PROVIDER}. Must be 'gemini' or 'anthropic'"
            )

    async def connect_to_server(self):
        """Connect to the MCP Weather Server via stdio."""
        # Prepare environment with API key for authentication
        server_env = os.environ.copy()

        # Pass client API key to server if configured
        client_api_key = os.getenv("MCP_CLIENT_API_KEY")
        if client_api_key:
            server_env["MCP_CLIENT_API_KEY"] = client_api_key
            print("🔒 Authenticating with MCP server...", file=sys.stderr)

        server_params = StdioServerParameters(
            command="python",
            args=["-m", "server.weather_server"],
            env=server_env  # Pass environment with API key
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print(f"\n✅ Connected to MCP Weather Server", file=sys.stderr)
        print(
            f"🤖 AI Provider: {self.provider.get_name()}", file=sys.stderr
        )
        print(
            f"📦 Available tools: {', '.join(tool.name for tool in tools)}\n",
            file=sys.stderr,
        )

        return tools

    async def process_query(self, query: str, tools: list):
        """Process a weather query using the AI provider."""
        print(f"🤔 Query: {query}\n")

        try:
            response = await self.provider.process_query(query, tools, self.session)
            print(f"🤖 Response:\n{response}\n")
        except Exception as e:
            print(f"❌ Error processing query: {e}\n", file=sys.stderr)

    async def run_interactive(self):
        """Run the client in interactive mode."""
        tools = await self.connect_to_server()

        print("=" * 60)
        print(f"🌤️  MCP Weather Demo - Interactive Mode")
        print(f"🤖 Powered by: {self.provider.get_name()}")
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
        """Run a demo with pre-defined queries."""
        tools = await self.connect_to_server()

        demo_queries = [
            "What's the current weather in San Francisco?",
            "Give me a 5-day forecast for Tokyo",
            "What's the weather at coordinates 51.5074, -0.1278?",  # London
        ]

        print("=" * 60)
        print("🌤️  MCP Weather Demo - Automated Demo")
        print(f"🤖 Powered by: {self.provider.get_name()}")
        print("=" * 60)
        print()

        for query in demo_queries:
            await self.process_query(query, tools)
            print("-" * 60)
            print()
            await asyncio.sleep(1)

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main entry point."""
    # Print available providers
    print("🔧 Checking AI provider configuration...", file=sys.stderr)
    print(f"   AI_PROVIDER={AI_PROVIDER}", file=sys.stderr)

    try:
        client = WeatherClient()

        if len(sys.argv) > 1 and sys.argv[1] == "--demo":
            await client.run_demo()
        else:
            await client.run_interactive()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}", file=sys.stderr)
        print("\nPlease set up your .env file with:", file=sys.stderr)
        print("  - AI_PROVIDER=gemini (or anthropic)", file=sys.stderr)
        print("  - GEMINI_API_KEY=... (if using Gemini)", file=sys.stderr)
        print("  - ANTHROPIC_API_KEY=... (if using Anthropic)", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Missing Package: {e}", file=sys.stderr)
        print("\nRun: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)
    finally:
        if "client" in locals():
            await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
