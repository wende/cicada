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
    # Create server with test fixtures config using centralized storage
    import json

    import yaml

    from cicada.utils.storage import (
        get_config_path,
        get_index_path,
        get_storage_dir,
    )

    fixture_dir = Path(__file__).parent.parent / "fixtures" / "test_project"
    if not fixture_dir.exists():
        fixture_dir = Path(__file__).parent.parent / "fixtures" / "elixir_project"

    # Create centralized storage for the fixture
    storage_dir = get_storage_dir(fixture_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal index (will be overridden below anyway)
    minimal_index = {
        "modules": {},
        "metadata": {"total_modules": 0, "repo_path": str(fixture_dir)},
    }
    index_path = get_index_path(fixture_dir)
    with open(index_path, "w") as f:
        json.dump(minimal_index, f)

    # Create config
    config_path = get_config_path(fixture_dir)
    test_config = {"repository": {"path": str(fixture_dir)}}
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)

    server = CicadaServer(config_path=str(config_path))

    # Override index to use test index
    test_index_path = Path(__file__).parent.parent / "data" / "test_index.json"
    with open(test_index_path) as f:
        server.index = json.load(f)

    print("Testing aliased call resolution...\n")

    # Test 1: Search for MyApp.User.new (called via User alias)
    print("=" * 60)
    print("Test 1: Search for 'new' in MyApp.User (called via 'User' alias)")
    print("=" * 60)
    result = await server.function_handler.search_function("new", "markdown")
    # Filter to only show MyApp.User results
    print(result[0].text[:1500])
    print()

    # Test 2: Search for insert (called via DB alias)
    print("=" * 60)
    print("Test 2: Search for 'insert' (called via 'DB' alias)")
    print("=" * 60)
    result = await server.function_handler.search_function("insert", "markdown")
    print(result[0].text)
    print()


if __name__ == "__main__":
    asyncio.run(test_aliased_calls())
