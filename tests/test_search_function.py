#!/usr/bin/env python
"""
Test script for search_function MCP tool.
"""
import asyncio
import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp_server import CicadaServer


@pytest.mark.asyncio
async def test_search_function():
    """Test the search_function tool."""
    # Create server with test index
    server = CicadaServer(config_path="config.yaml")

    # Override index to use test index
    import json

    with open("data/test_index.json", "r") as f:
        server.index = json.load(f)

    print("Testing search_function tool...\n")

    # Test 1: Search for create_user with usage examples
    print("Test 1: Search for 'create_user' with usage examples")
    result = await server._search_function(
        "create_user", "markdown", include_usage_examples=True, max_examples=3
    )
    print(result[0].text)
    print()

    # Test 2: Search for create_user/2 (with arity)
    print("Test 2: Search for 'create_user/2'")
    result = await server._search_function("create_user/2", "json")
    print(result[0].text)
    print()

    # Test 3: Search for find_user
    print("Test 3: Search for 'find_user'")
    result = await server._search_function("find_user", "markdown")
    print(result[0].text)
    print()

    # Test 4: Search for a function that doesn't exist
    print("Test 4: Search for non-existent function")
    result = await server._search_function("nonexistent_function", "markdown")
    print(result[0].text)
    print()


if __name__ == "__main__":
    asyncio.run(test_search_function())
