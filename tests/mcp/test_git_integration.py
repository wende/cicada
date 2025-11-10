"""
Integration tests for MCP server git history functionality.
"""

import asyncio
import json
import os

import pytest
import yaml

from cicada.mcp.server import CicadaServer


@pytest.fixture
def test_server():
    """Fixture to create a test MCP server instance."""
    # Use the shared index created by conftest.py
    # Create a test config
    test_config = {
        "repository": {"path": "."},
        "storage": {"index_path": ".cicada/index.json"},
    }

    test_config_path = "test_mcp_git_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        server = CicadaServer(test_config_path)
        yield server
    finally:
        # Cleanup - only remove the config file, not the shared index
        if os.path.exists(test_config_path):
            os.remove(test_config_path)


def test_server_has_git_helper(test_server):
    """Test that the server initializes GitHelper."""
    print("Testing server has git_helper...")

    assert hasattr(test_server, "git_helper"), "Server should have git_helper attribute"
    assert test_server.git_helper is not None, "GitHelper should be initialized"

    print("  ✓ Server has GitHelper initialized")


def test_list_tools_includes_get_commit_history(test_server):
    """Test that get_commit_history tool is registered."""
    print("\nTesting get_commit_history tool registration...")

    tools = asyncio.run(test_server.list_tools())

    # Find get_commit_history tool
    git_tool = None
    for tool in tools:
        if tool.name == "get_commit_history":
            git_tool = tool
            break

    assert git_tool is not None, "get_commit_history tool not found in tool list"
    assert (
        "git history" in git_tool.description.lower()
    ), "Tool description should mention git history"

    # Check required parameters
    assert "file_path" in git_tool.inputSchema["properties"], "Tool should have file_path parameter"

    print("  ✓ get_commit_history tool is registered")
    print(f"  ✓ Tool description: {git_tool.description[:100]}...")


def test_get_commit_history_basic(test_server):
    """Test basic file history retrieval."""
    print("\nTesting basic file history...")

    result = asyncio.run(test_server._get_file_history("README.md", max_commits=3))

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"

    text = result[0].text
    assert "Git History for README.md" in text, "Should contain file name in title"
    assert "commit(s)" in text.lower(), "Should mention commits"
    assert "Commit:" in text, "Should include commit information"
    assert "Author:" in text, "Should include author information"

    print("  ✓ File history retrieved successfully")
    print(f"  ✓ Response length: {len(text)} characters")


def test_get_commit_history_with_limit(test_server):
    """Test that max_commits parameter is respected."""
    print("\nTesting max_commits parameter...")

    # Get history with limit of 2
    result = asyncio.run(test_server._get_file_history("README.md", max_commits=2))

    text = result[0].text

    # Count how many commits are in the response by counting "## " (markdown headers for commits)
    commit_count = text.count("## ") - 1  # Subtract 1 for the main title

    assert commit_count <= 2, f"Should have at most 2 commits, found {commit_count}"

    print(f"  ✓ Returned {commit_count} commit(s) (max 2)")


def test_get_commit_history_function_specific(test_server):
    """Test function-specific history retrieval."""
    print("\nTesting function-specific history...")

    # Use a file that actually has history - cicada/mcp_server.py
    result = asyncio.run(
        test_server._get_file_history(
            "cicada/mcp_server.py",
            function_name="__init__",
            start_line=25,
            max_commits=2,
        )
    )

    assert len(result) == 1, "Should return one TextContent"
    text = result[0].text

    # Check that it mentions the function or file name
    assert "__init__" in text or "mcp_server.py" in text, "Should mention function or file name"

    # If commits were found, check for proper formatting
    if "No commit history found" not in text:
        assert "Git History for" in text, "Should have title when commits found"
        if "Relevance:" in text:
            assert "🎯" in text or "📝" in text, "Should include relevance emoji indicators"
            print("  ✓ Function-specific history with relevance indicators")
        else:
            print("  ✓ Function-specific history retrieved")
    else:
        print("  ✓ Function history returned (no commits found for this range)")


def test_get_commit_history_nonexistent_file(test_server):
    """Test handling of non-existent file."""
    print("\nTesting non-existent file handling...")

    result = asyncio.run(test_server._get_file_history("nonexistent_file.txt", max_commits=5))

    assert len(result) == 1, "Should return one TextContent"
    text = result[0].text

    assert "No commit history found" in text, "Should indicate no commits found"

    print("  ✓ Non-existent file handled gracefully")


def test_call_tool_get_commit_history(test_server):
    """Test calling get_commit_history via the call_tool interface."""
    print("\nTesting call_tool interface for get_commit_history...")

    arguments = {"file_path": "README.md", "max_commits": 2}

    result = asyncio.run(test_server.call_tool("get_commit_history", arguments))

    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text", "Should return text content"
    assert "Git History" in result[0].text, "Should contain git history"

    print("  ✓ call_tool interface working")


def test_call_tool_missing_file_path(test_server):
    """Test error handling when file_path is missing."""
    print("\nTesting missing file_path error...")

    arguments = {
        "max_commits": 5
        # Missing 'file_path'
    }

    result = asyncio.run(test_server.call_tool("get_commit_history", arguments))

    assert len(result) == 1, "Should return one TextContent"
    text = result[0].text
    assert "file_path" in text.lower(), "Error message should mention file_path"
    assert "required" in text.lower(), "Error message should mention it's required"

    print("  ✓ Missing parameter error handled correctly")


def test_git_helper_not_available():
    """Test behavior when git helper is not available."""
    print("\nTesting behavior when git is not available...")

    # Create a unique minimal valid index for this test
    os.makedirs(".cicada", exist_ok=True)

    minimal_index = {
        "modules": {},
        "metadata": {"total_modules": 0, "repo_path": "/tmp"},
    }

    # Use a unique index file for this test
    index_path = ".cicada/test_nogit_index.json"
    with open(index_path, "w") as f:
        json.dump(minimal_index, f)

    # Create a config pointing to a non-git directory
    test_config = {
        "repository": {"path": "/tmp"},
        "storage": {"index_path": index_path},
    }

    test_config_path = "test_nogit_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        server = CicadaServer(test_config_path)

        # git_helper should be None
        assert server.git_helper is None, "git_helper should be None for non-git repo"

        # Try to get file history
        result = asyncio.run(server._get_file_history("README.md"))

        text = result[0].text
        assert "not available" in text.lower(), "Should indicate git is not available"

        print("  ✓ Non-git repo handled gracefully")

    finally:
        # Clean up test-specific files only
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
        if os.path.exists(index_path):
            os.remove(index_path)


def test_get_commit_history_markdown_format(test_server):
    """Test that the output is properly formatted markdown."""
    print("\nTesting markdown formatting...")

    result = asyncio.run(test_server._get_file_history("README.md", max_commits=2))
    text = result[0].text

    # Check for markdown elements
    assert text.startswith("# "), "Should start with h1 header"
    assert "## " in text, "Should have h2 headers for commits"
    assert "- **" in text, "Should have bold list items"
    assert "`" in text, "Should have code formatting for SHA"

    # Check structure
    lines = text.split("\n")
    assert lines[0].startswith("# Git History"), "First line should be title"

    print("  ✓ Output is properly formatted markdown")


def test_multiple_files_history(test_server):
    """Test getting history for multiple files."""
    print("\nTesting multiple file histories...")

    files = ["README.md", "pyproject.toml", "cicada/mcp_server.py"]

    for file_path in files:
        result = asyncio.run(test_server._get_file_history(file_path, max_commits=1))

        assert len(result) == 1, f"Should return result for {file_path}"
        text = result[0].text
        assert file_path in text, f"Should mention {file_path}"

        print(f"  ✓ Retrieved history for {file_path}")


def test_git_history_includes_all_fields(test_server):
    """Test that git history includes all expected fields."""
    print("\nTesting completeness of git history data...")

    result = asyncio.run(test_server._get_file_history("README.md", max_commits=1))
    text = result[0].text

    # Check for all expected fields in the output
    expected_fields = [
        "Commit:",
        "Author:",
        "Date:",
    ]

    for field in expected_fields:
        assert field in text, f"Output should include '{field}'"

    print("  ✓ All expected fields present in output")


if __name__ == "__main__":
    print("Running MCP git integration tests...\n")

    # Create a minimal valid index for standalone testing
    os.makedirs(".cicada", exist_ok=True)

    minimal_index = {"modules": {}, "metadata": {"total_modules": 0, "repo_path": "."}}

    # Use a unique index file for standalone execution
    index_path = ".cicada/test_standalone_index.json"
    with open(index_path, "w") as f:
        json.dump(minimal_index, f)

    # Create a test server for standalone execution
    test_config = {"repository": {"path": "."}, "storage": {"index_path": index_path}}

    test_config_path = "test_mcp_git_config.yaml"
    with open(test_config_path, "w") as f:
        yaml.dump(test_config, f)

    try:
        server = CicadaServer(test_config_path)

        # Run all tests
        test_server_has_git_helper(server)
        test_list_tools_includes_get_commit_history(server)
        test_get_commit_history_basic(server)
        test_get_commit_history_with_limit(server)
        test_get_commit_history_function_specific(server)
        test_get_commit_history_nonexistent_file(server)
        test_call_tool_get_commit_history(server)
        test_call_tool_missing_file_path(server)
        test_git_helper_not_available()
        test_get_commit_history_markdown_format(server)
        test_multiple_files_history(server)
        test_git_history_includes_all_fields(server)

        print("\n" + "=" * 50)
        print("All MCP git integration tests passed!")
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
    finally:
        # Cleanup - remove test-specific files only
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
        if os.path.exists(index_path):
            os.remove(index_path)
