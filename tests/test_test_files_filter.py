#!/usr/bin/env python
"""
Test script for test_files_only parameter in search_function MCP tool.
"""
import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp.server import CicadaServer


@pytest.mark.asyncio
async def test_test_files_filter(tmp_path):
    """Test the test_files_only parameter in search_function."""
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

    print("Testing test_files_only parameter...\n")

    # Test 1: Search without test filter (show all call sites)
    print("=" * 60)
    print("Test 1: Search for function - ALL call sites")
    print("=" * 60)
    # Pick a function that exists in your index
    result = await server._search_function(
        "create_user",  # Replace with a function name from your actual index
        output_format="markdown",
        include_usage_examples=False,
        max_examples=5,
        test_files_only=False,
    )
    print(result[0].text)
    print()

    # Test 2: Search WITH test filter (only test files)
    print("=" * 60)
    print("Test 2: Search for same function - TEST FILES ONLY")
    print("=" * 60)
    result = await server._search_function(
        "create_user",  # Same function
        output_format="markdown",
        include_usage_examples=False,
        max_examples=5,
        test_files_only=True,
    )
    print(result[0].text)
    print()

    # Test 3: With usage examples and test filter
    print("=" * 60)
    print("Test 3: With usage examples from test files only")
    print("=" * 60)
    result = await server._search_function(
        "create_user",
        output_format="markdown",
        include_usage_examples=True,
        max_examples=3,
        test_files_only=True,
    )
    print(result[0].text)
    print()


if __name__ == "__main__":
    asyncio.run(test_test_files_filter())
