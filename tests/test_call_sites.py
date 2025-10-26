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

from cicada.mcp_server import CicadaServer


@pytest.mark.asyncio
async def test_call_sites():
    """Test the call site resolution."""
    # Create server with test index
    server = CicadaServer(config_path="config.yaml")

    # Override index to use test index
    import json

    with open("data/test_index.json", "r") as f:
        server.index = json.load(f)

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
