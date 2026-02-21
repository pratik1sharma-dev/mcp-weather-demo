"""
Authentication module for MCP Weather Server

Implements API key-based authentication for securing MCP server access.
"""

import hashlib
import os
import secrets
from typing import Optional


class AuthManager:
    """
    Manages authentication for MCP server.

    Supports:
    - API key validation
    - Key hashing for secure storage
    - Multiple valid keys
    """

    def __init__(self, api_keys: Optional[list[str]] = None):
        """
        Initialize auth manager.

        Args:
            api_keys: List of valid API keys. If None, loads from environment.
        """
        if api_keys is None:
            # Load from environment
            keys_str = os.getenv("MCP_SERVER_API_KEYS", "")
            if keys_str:
                self.api_keys = set(keys_str.split(","))
            else:
                self.api_keys = set()
        else:
            self.api_keys = set(api_keys)

        # Hash the keys for secure comparison
        self.api_key_hashes = {self._hash_key(key) for key in self.api_keys}

    def _hash_key(self, key: str) -> str:
        """
        Hash an API key for secure storage.

        Args:
            key: API key to hash

        Returns:
            SHA256 hash of the key
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, provided_key: str) -> bool:
        """
        Validate a provided API key.

        Args:
            provided_key: API key from client

        Returns:
            True if valid, False otherwise
        """
        if not self.api_keys:
            # No authentication configured - allow all
            return True

        if not provided_key:
            return False

        # Compare hashed version
        provided_hash = self._hash_key(provided_key)
        return provided_hash in self.api_key_hashes

    def is_enabled(self) -> bool:
        """
        Check if authentication is enabled.

        Returns:
            True if authentication is configured, False otherwise
        """
        return len(self.api_keys) > 0

    @staticmethod
    def generate_key() -> str:
        """
        Generate a secure random API key.

        Returns:
            A secure random API key (32 characters)
        """
        return secrets.token_urlsafe(32)


def validate_request(api_key: str, auth_manager: AuthManager) -> tuple[bool, str]:
    """
    Validate an incoming request.

    Args:
        api_key: API key from client
        auth_manager: AuthManager instance

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not auth_manager.is_enabled():
        return True, ""

    if not api_key:
        return False, "Missing API key. Set MCP_CLIENT_API_KEY in client environment."

    if not auth_manager.validate_key(api_key):
        return False, "Invalid API key. Access denied."

    return True, ""
