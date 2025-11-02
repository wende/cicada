#!/usr/bin/env python
"""
Test script for aliased function calls.
"""
import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp.server import CicadaServer


@pytest.mark.asyncio
async def test_aliased_calls():
    """Test the aliased call resolution."""
    # Create server with test fixtures config
    config_path = Path(__file__).parent / "fixtures" / ".cicada" / "config.yaml"
    server = CicadaServer(config_path=str(config_path))

    # Override index to use test index
    import json

    test_index_path = Path(__file__).parent.parent / "data" / "test_index.json"
    with open(test_index_path) as f:
        server.index = json.load(f)

    print("Testing aliased call resolution...\n")

    # Test 1: Search for MyApp.User.new (called via User alias)
    print("=" * 60)
    print("Test 1: Search for 'new' in MyApp.User (called via 'User' alias)")
    print("=" * 60)
    result = await server._search_function("new", "markdown")
    # Filter to only show MyApp.User results
    print(result[0].text[:1500])
    print()

    # Test 2: Search for insert (called via DB alias)
    print("=" * 60)
    print("Test 2: Search for 'insert' (called via 'DB' alias)")
    print("=" * 60)
    result = await server._search_function("insert", "markdown")
    print(result[0].text)
    print()


if __name__ == "__main__":
    asyncio.run(test_aliased_calls())
