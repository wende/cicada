"""
End-to-end integration tests for Cicada.
"""

import os
from pathlib import Path

import pytest
import yaml

from cicada.indexer import ElixirIndexer
from cicada.mcp.server import CicadaServer


@pytest.fixture
def index_path():
    """Fixture to create test index."""
    indexer = ElixirIndexer()
    output_path = "data/test_e2e_index.json"
    indexer.index_repository("tests/fixtures", output_path)
    yield output_path


def test_indexer():
    """Test that the indexer creates a valid index."""
    print("Testing indexer...")

    # Index test fixtures
    indexer = ElixirIndexer()
    output_path = "data/test_e2e_index.json"

    index = indexer.index_repository("tests/fixtures", output_path)

    # Verify index exists
    assert Path(output_path).exists(), "Index file was not created"

    # Verify index structure
    assert "modules" in index, "Index missing 'modules' key"
    assert "metadata" in index, "Index missing 'metadata' key"

    # Verify we indexed the Test module
    assert "Test" in index["modules"], "Test module not found in index"

    # Verify Test module data
    test_module = index["modules"]["Test"]
    assert test_module["file"] == "sample.ex"
    assert test_module["total_functions"] == 5
    assert test_module["public_functions"] == 3
    assert test_module["private_functions"] == 2

    # Verify functions are present
    functions = test_module["functions"]
    assert len(functions) == 5

    function_names = [f["name"] for f in functions]
    assert "hello" in function_names
    assert "private_func" in function_names
    assert "multi_arity" in function_names

    print("  ✓ Index created successfully")
    print(f"  ✓ Found {len(index['modules'])} module(s)")
    print(f"  ✓ Total functions: {index['metadata']['total_functions']}")


def test_mcp_server_initialization(index_path):
    """Test that the MCP server can initialize and load the index."""
    print("\nTesting MCP server initialization...")

    # Create a temporary config for testing
    test_config = {
        "repository": {"path": "/Users/wende/projects/ab"},
        "storage": {"index_path": index_path},
    }

    test_config_path = "test_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        # Initialize server
        server = CicadaServer(test_config_path)

        # Verify index was loaded
        assert server.index is not None, "Index not loaded"
        assert "modules" in server.index, "Index missing modules"

        print("  ✓ Server initialized successfully")
        print(f"  ✓ Loaded {len(server.index['modules'])} module(s)")

    finally:
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)


def test_module_not_found():
    """Test error handling when module is not found."""
    print("\nTesting module not found error...")

    test_config = {
        "repository": {"path": "/Users/wende/projects/ab"},
        "storage": {"index_path": "data/test_e2e_index.json"},
    }

    import yaml

    test_config_path = "test_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        server = CicadaServer(test_config_path)

        # Search for non-existent module
        import asyncio

        result = asyncio.run(server._search_module("NonExistent.Module"))

        # Check the markdown response
        response_text = result[0].text

        assert "Module Not Found" in response_text, "Error message not in response"
        assert "NonExistent.Module" in response_text, "Query module name not in response"

        print("  ✓ Module not found error handled correctly")

    finally:
        if os.path.exists(test_config_path):
            os.remove(test_config_path)


if __name__ == "__main__":
    print("Running end-to-end tests...\n")

    try:
        # Test indexer
        test_indexer()
        index_path = "data/test_e2e_index.json"

        # Test MCP server
        test_mcp_server_initialization(index_path)

        # Test error handling
        test_module_not_found()

        print("\n" + "=" * 50)
        print("All end-to-end tests passed!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
