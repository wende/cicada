"""
End-to-end integration tests for Cicada.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from cicada.indexer import ElixirIndexer
from cicada.mcp.server import CicadaServer


def write_minimal_elixir_repo(repo_path: Path) -> None:
    """Create a tiny Elixir repo for tests that only need a valid index."""
    (repo_path / "sample.ex").write_text(
        """
defmodule Test do
  def hello do
    "world"
  end
end
""".strip()
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def index_path(tmp_path):
    """Fixture to create test index."""
    write_minimal_elixir_repo(tmp_path)
    indexer = ElixirIndexer()
    output_path = tmp_path / "test_e2e_index.json"
    indexer.index_repository(str(tmp_path), str(output_path))
    yield str(output_path)


def test_indexer(tmp_path):
    """Test that the indexer creates a valid index."""
    print("Testing indexer...")

    # Index test fixtures
    indexer = ElixirIndexer()
    output_path = tmp_path / "test_e2e_index.json"

    index = indexer.index_repository("tests/fixtures", str(output_path))

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

    # Verify functions are present
    functions = test_module["functions"]
    assert len(functions) == 5

    # Check we have the expected number of public and private functions
    public_count = sum(1 for f in functions if f.get("type") == "def")
    private_count = sum(1 for f in functions if f.get("type") == "defp")
    assert public_count == 3
    assert private_count == 2

    function_names = [f["name"] for f in functions]
    assert "hello" in function_names
    assert "private_func" in function_names
    assert "multi_arity" in function_names

    print("  ✓ Index created successfully")
    print(f"  ✓ Found {len(index['modules'])} module(s)")

    # Count total functions across all modules
    total_funcs = sum(len(m.get("functions", [])) for m in index["modules"].values())
    print(f"  ✓ Total functions: {total_funcs}")


def test_mcp_server_initialization(index_path, tmp_path):
    """Test that the MCP server can initialize and load the index."""
    print("\nTesting MCP server initialization...")

    # Create a temporary config for testing
    test_config = {
        "repository": {"path": "/Users/wende/projects/ab"},
        "storage": {"index_path": index_path},
    }

    test_config_path = tmp_path / "test_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        # Initialize server
        server = CicadaServer(str(test_config_path))

        # Verify index was loaded
        assert server.index_manager.index is not None, "Index not loaded"
        assert "modules" in server.index_manager.index, "Index missing modules"

        print("  ✓ Server initialized successfully")
        print(f"  ✓ Loaded {len(server.index_manager.index['modules'])} module(s)")

    finally:
        # Cleanup
        if test_config_path.exists():
            test_config_path.unlink()


def test_module_not_found(tmp_path):
    """Test error handling when module is not found."""
    print("\nTesting module not found error...")

    # First create an index
    indexer = ElixirIndexer()
    index_path = tmp_path / "test_e2e_index.json"
    indexer.index_repository("tests/fixtures", str(index_path))

    test_config = {
        "repository": {"path": "/Users/wende/projects/ab"},
        "storage": {"index_path": str(index_path)},
    }

    import yaml

    test_config_path = tmp_path / "test_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        server = CicadaServer(str(test_config_path))

        # Search for non-existent module
        import asyncio

        result = asyncio.run(server.module_handler.search_module("NonExistent.Module"))

        # Check the markdown response
        response_text = result[0].text

        assert "Module Not Found" in response_text, "Error message not in response"
        assert "NonExistent.Module" in response_text, "Query module name not in response"

        print("  ✓ Module not found error handled correctly")

    finally:
        if test_config_path.exists():
            test_config_path.unlink()


if __name__ == "__main__":
    print("Running end-to-end tests...\n")

    try:
        tmp_dir = Path(tempfile.mkdtemp())

        # Test indexer
        test_indexer(tmp_dir)
        index_path = str(tmp_dir / "test_e2e_index.json")

        # Test MCP server
        test_mcp_server_initialization(index_path, tmp_dir)

        # Test error handling
        test_module_not_found(tmp_dir)

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
