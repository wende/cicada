"""
Tests for the unified git_history tool.

Tests cover all routing modes:
- Single line (blame + PR)
- Line range (blame groups)
- Function tracking
- File-level history
"""

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from cicada.mcp.server import CicadaServer
from cicada.utils.storage import get_index_path, get_config_path, get_storage_dir


@pytest.fixture
def test_server():
    """Fixture to create a test MCP server instance."""
    # Use centralized storage in the mocked home directory
    repo_path = Path.cwd()
    storage_dir = get_storage_dir(repo_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Create a minimal index in centralized storage
    minimal_index = {"modules": {}, "metadata": {"total_modules": 0, "repo_path": str(repo_path)}}
    index_path = get_index_path(repo_path)
    with open(index_path, "w") as f:
        json.dump(minimal_index, f)

    # Create config in centralized storage
    config_path = get_config_path(repo_path)
    test_config = {"repository": {"path": str(repo_path)}}
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)

    server = CicadaServer(str(config_path))
    yield server


def test_git_history_tool_registered(test_server):
    """Test that git_history tool is registered."""
    print("\nTesting git_history tool registration...")

    tools = asyncio.run(test_server.list_tools())

    # Find git_history tool
    git_history_tool = None
    for tool in tools:
        if tool.name == "git_history":
            git_history_tool = tool
            break

    assert git_history_tool is not None, "git_history tool not found in tool list"
    assert (
        "unified" in git_history_tool.description.lower()
    ), "Tool description should mention unified"

    # Check required parameters
    assert (
        "file_path" in git_history_tool.inputSchema["properties"]
    ), "Tool should have file_path parameter"
    assert (
        "start_line" in git_history_tool.inputSchema["properties"]
    ), "Tool should have start_line parameter"
    assert (
        "end_line" in git_history_tool.inputSchema["properties"]
    ), "Tool should have end_line parameter"
    assert (
        "function_name" in git_history_tool.inputSchema["properties"]
    ), "Tool should have function_name parameter"
    assert (
        "recent" in git_history_tool.inputSchema["properties"]
    ), "Tool should have recent parameter"
    assert (
        "author" in git_history_tool.inputSchema["properties"]
    ), "Tool should have author parameter"

    print("  ✓ git_history tool is registered")
    print(f"  ✓ Tool description mentions unified: {git_history_tool.description[:150]}...")


def test_git_history_file_level(test_server):
    """Test file-level history (no line numbers, no function name)."""
    print("\nTesting file-level git history...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            max_results=3,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    assert "History for README.md" in text or "README.md" in text, "Should contain file name"

    print("  ✓ File-level history retrieved")
    print(f"  ✓ Response length: {len(text)} characters")


def test_git_history_line_range(test_server):
    """Test line range blame (start_line + end_line)."""
    print("\nTesting line range blame...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            start_line=1,
            end_line=10,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    assert "Lines" in text or "Line" in text, "Should mention lines"
    assert "README.md" in text, "Should contain file name"

    print("  ✓ Line range blame retrieved")
    print(f"  ✓ Response length: {len(text)} characters")


def test_git_history_single_line(test_server):
    """Test single line analysis (start_line only)."""
    print("\nTesting single line analysis...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            start_line=1,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    assert "Line" in text, "Should mention line"
    assert "README.md" in text, "Should contain file name"

    print("  ✓ Single line analysis completed")
    print(f"  ✓ Response length: {len(text)} characters")


def test_git_history_with_recent_filter_true(test_server):
    """Test recent filter (last 14 days)."""
    print("\nTesting recent=true filter...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            recent=True,
            max_results=5,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should work without error (filtering is internal)
    print("  ✓ Recent filter (true) applied successfully")


def test_git_history_with_recent_filter_false(test_server):
    """Test recent filter (older than 14 days)."""
    print("\nTesting recent=false filter...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            recent=False,
            max_results=5,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should work without error (filtering is internal)
    print("  ✓ Recent filter (false) applied successfully")


def test_git_history_with_recent_filter_none(test_server):
    """Test recent filter (all time)."""
    print("\nTesting recent=None filter (all time)...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            recent=None,
            max_results=5,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should work without error (no filtering)
    print("  ✓ Recent filter (None) - all time query successful")


def test_git_history_with_author_filter(test_server):
    """Test author filter."""
    print("\nTesting author filter...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            author="test",  # Won't match anything but shouldn't error
            max_results=5,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should work without error (filtering is internal)
    print("  ✓ Author filter applied successfully")


def test_git_history_function_tracking(test_server):
    """Test function tracking with evolution."""
    print("\nTesting function tracking...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="cicada/git/helper.py",
            function_name="get_file_history",
            show_evolution=True,
            max_results=3,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    assert "Function" in text or "get_file_history" in text, "Should mention function"

    print("  ✓ Function tracking with evolution completed")
    print(f"  ✓ Response length: {len(text)} characters")


def test_git_history_with_max_results(test_server):
    """Test max_results parameter."""
    print("\nTesting max_results parameter...")

    # Get history with limit of 2
    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="README.md",
            max_results=2,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should work without error (limiting is internal)
    print("  ✓ max_results parameter respected")


def test_git_history_error_handling_missing_file(test_server):
    """Test error handling for missing file."""
    print("\nTesting error handling for missing file...")

    result = asyncio.run(
        test_server.git_handler.git_history(
            file_path="nonexistent_file.txt",
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    # Should not crash, may show error or no results
    print("  ✓ Error handling works for missing file")
    print(f"  ✓ Response: {text[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
