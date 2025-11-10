#!/usr/bin/env python
"""
Test script for function call sites.
"""
import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp.server import CicadaServer


@pytest.mark.asyncio
async def test_call_sites(tmp_path):
    """Test the call site resolution."""
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

    print("Testing call site resolution...\n")

    # Test 1: Search for validate_email (has local call) with usage examples
    print("Test 1: Search for 'validate_email' (local call) with usage examples")
    result = await server._search_function(
        "validate_email", "markdown", include_usage_examples=True, max_examples=5
    )
    print(result[0].text)
    print()

    # Test 2: JSON format
    print("Test 2: JSON format for 'validate_email'")
    result = await server._search_function("validate_email", "json")
    print(result[0].text)
    print()


if __name__ == "__main__":
    asyncio.run(test_call_sites())
