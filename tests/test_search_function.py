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

from cicada.mcp.server import CicadaServer


@pytest.mark.asyncio
async def test_search_function(tmp_path):
    """Test the search_function tool."""
    # Load test index
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Create server with test index
    server = CicadaServer(config_path=str(config_path))

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

    # Test 5: Search with wildcard pattern
    print("Test 5: Search for 'create*' (wildcard pattern)")
    result = await server._search_function("create*", "markdown")
    print(result[0].text)
    print()

    # Test 6: Search with OR pattern
    print("Test 6: Search for 'create_user|find_user' (OR pattern)")
    result = await server._search_function("create_user|find_user", "markdown")
    print(result[0].text)
    print()

    # Test 7: Search with wildcard OR pattern
    print("Test 7: Search for 'create*|find*' (wildcard OR pattern)")
    result = await server._search_function("create*|find*", "markdown")
    print(result[0].text)
    print()


@pytest.mark.asyncio
async def test_wildcard_function_search(tmp_path):
    """Test wildcard functionality in function search."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Test wildcard pattern matching
    result = await server._search_function("create*", "markdown")
    assert result[0].text
    # Should find functions starting with "create"
    assert "create" in result[0].text.lower()

    # Test OR pattern
    result = await server._search_function("create*|find*", "markdown")
    assert result[0].text
    # Should find both create and find functions


@pytest.mark.asyncio
async def test_wildcard_module_search(tmp_path):
    """Test wildcard functionality in module search."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Get module names from test index
    module_names = list(test_index["modules"].keys())

    if module_names:
        # Test wildcard pattern - match all modules with a prefix
        if "." in module_names[0]:
            prefix = module_names[0].split(".")[0]
            result = await server._search_module(f"{prefix}.*", "markdown")
            assert result[0].text
            # Should find modules with that prefix
            assert "Found" in result[0].text or prefix in result[0].text

        # Test OR pattern
        if len(module_names) >= 2:
            result = await server._search_module(f"{module_names[0]}|{module_names[1]}", "markdown")
            assert result[0].text
            # Should find both modules


if __name__ == "__main__":
    asyncio.run(test_search_function())
