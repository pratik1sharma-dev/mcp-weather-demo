#!/usr/bin/env python3
"""
API Key Generator for MCP Weather Server

Generates a cryptographically secure API key for authentication.
"""

import secrets


def main():
    """Generate and display an API key."""
    print("🔐 MCP Weather Server - API Key Generator")
    print("=" * 50)
    print()

    # Generate a secure key
    api_key = secrets.token_urlsafe(32)

    print("Generated API Key:")
    print()
    print(f"  {api_key}")
    print()
    print("=" * 50)
    print()
    print("📋 Add to your .env file:")
    print()
    print("SERVER SIDE (to enable authentication):")
    print(f"  MCP_SERVER_API_KEYS={api_key}")
    print()
    print("CLIENT SIDE (to authenticate):")
    print(f"  MCP_CLIENT_API_KEY={api_key}")
    print()
    print("💡 Tips:")
    print("  • Keep this key secure (never commit to git)")
    print("  • You can generate multiple keys (comma-separated)")
    print("  • Leave MCP_SERVER_API_KEYS empty to disable auth")
    print()


if __name__ == "__main__":
    main()
