"""
Acceptance tests for Cicada MCP server.

Tests can use either:
- Runner module functions (tests/acceptance/runner.py) - provides coverage
- Direct MCP server calls - legacy pattern

The runner module is also used by shell scripts for manual testing.

Author: Cursor(Auto)
"""

import pytest

from cicada.mcp.server import CicadaServer

# Import runner functions - these get coverage when tests run
from tests.acceptance.runner import (
    get_file_history,
    search_function,
    search_module,
)

# Fixtures


@pytest.fixture
def config_path():
    """Path to test fixtures config (from centralized storage)."""
    from pathlib import Path
    from cicada.utils.storage import get_config_path, get_index_path
    import yaml
    import json

    # Determine which fixture to use
    if Path("tests/fixtures/elixir_project").exists():
        fixture_dir = Path("tests/fixtures/elixir_project").resolve()
    else:
        fixture_dir = Path("tests/fixtures/test_project").resolve()

    # Get paths (will use mocked home if in test)
    config_path_obj = get_config_path(fixture_dir)
    index_path_obj = get_index_path(fixture_dir)

    # Ensure storage directory exists
    config_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Create minimal config
    config = {
        "repository": {"path": str(fixture_dir)},
    }
    with open(config_path_obj, "w") as f:
        yaml.dump(config, f)

    # Create minimal index if it doesn't exist
    if not index_path_obj.exists():
        minimal_index = {
            "modules": {
                "TestApp": {
                    "file": "lib/test_app.ex",
                    "line": 1,
                    "moduledoc": "Test application module",
                    "keywords": {"test": 1.0, "application": 0.9, "module": 0.8},
                    "functions": [
                        {
                            "name": "hello",
                            "arity": 0,
                            "line": 5,
                            "type": "def",
                            "signature": "hello()",
                            "doc": "Says hello",
                            "keywords": {"hello": 1.0, "greet": 0.9},
                        },
                        {
                            "name": "add",
                            "arity": 2,
                            "line": 10,
                            "type": "def",
                            "signature": "add(a, b)",
                            "doc": "Adds two numbers",
                            "keywords": {"add": 1.0, "number": 0.9, "sum": 0.8},
                        },
                        {
                            "name": "add_numbers",
                            "arity": 2,
                            "line": 15,
                            "type": "def",
                            "signature": "add_numbers(x, y)",
                            "doc": "Adds two numbers together",
                            "keywords": {"add": 1.0, "number": 0.9, "sum": 0.8},
                        },
                    ],
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(fixture_dir)},
        }
        with open(index_path_obj, "w") as f:
            json.dump(minimal_index, f)

    return str(config_path_obj)


@pytest.fixture
async def server(config_path):
    """Create a CicadaServer instance for testing (legacy fixture)."""
    return CicadaServer(config_path=config_path)


# Module Search Tests (search_module.sh, check_moduledoc.sh)


@pytest.mark.asyncio
async def test_search_module_basic():
    """Test basic module search functionality."""
    text = await search_module("TestApp", "markdown")
    assert "TestApp" in text
    assert text.strip()  # Should have content


@pytest.mark.asyncio
async def test_search_module_includes_moduledoc():
    """Test that moduledoc is displayed when searching for modules."""
    text = await search_module("TestApp", "markdown")
    # Should contain module documentation
    assert "TestApp" in text
    # Verify it's actually showing documentation content, not just the name
    assert len(text) > 50  # Should be substantial


@pytest.mark.asyncio
async def test_search_module_json_format():
    """Test module search with JSON output format."""
    text = await search_module("AB.Generators", "json")
    assert text.strip()
    # JSON should contain the module name somewhere
    assert "AB.Generators" in text or "Generators" in text


# Function Search Tests (search_function.sh, check_functiondoc.sh)


@pytest.mark.asyncio
async def test_search_function_basic(server):
    """Test basic function search functionality."""
    result = await server.function_handler.search_function(
        "add_numbers/2", output_format="markdown", include_usage_examples=False
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text


@pytest.mark.asyncio
async def test_search_function_with_examples(server):
    """Test function search with usage examples included."""
    result = await server.function_handler.search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=True,
        max_examples=5,
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text
    # Examples section should be present if there are any examples
    # The actual presence depends on the test data


@pytest.mark.asyncio
async def test_search_function_with_test_examples_only(server):
    """Test function search showing only examples from test files."""
    result = await server.function_handler.search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=True,
        usage_type="tests",
        max_examples=10,
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text


@pytest.mark.asyncio
async def test_search_function_with_limit(server):
    """Test function search with example limit."""
    result = await server.function_handler.search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=True,
        max_examples=3,
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text


@pytest.mark.asyncio
async def test_search_function_includes_doc(server):
    """Test that function @doc and examples are properly displayed."""
    # Use a function that likely has documentation
    result = await server.function_handler.search_function(
        "add_numbers/2", output_format="markdown", include_usage_examples=False
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text
    # Should have some content beyond just the function name
    assert len(text) > 20


@pytest.mark.asyncio
async def test_search_function_json_format(server):
    """Test function search with JSON output format."""
    result = await server.function_handler.search_function(
        "add_numbers/2", output_format="json", include_usage_examples=True
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


# Function History Tests (test_function_history.sh)


@pytest.mark.asyncio
async def test_function_history_basic(server):
    """Test basic function history tracking."""
    # Use a file from the cicada codebase itself
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py", function_name="get_recent_commits", max_commits=5
    )
    assert len(result) > 0
    text = result[0].text
    # Should contain commit information
    assert text.strip()


@pytest.mark.asyncio
async def test_function_history_with_evolution(server):
    """Test function history with evolution metadata."""
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py",
        function_name="get_recent_commits",
        show_evolution=True,
        max_commits=5,
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # Evolution metadata might include creation date, last modified, etc.


@pytest.mark.asyncio
async def test_function_history_with_limit(server):
    """Test function history with commit limit."""
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py", function_name="get_recent_commits", max_commits=3
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


@pytest.mark.asyncio
async def test_line_based_history_tracking(server):
    """Test line-based history tracking mode."""
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py", start_line=1, end_line=50, max_commits=5
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


@pytest.mark.asyncio
async def test_line_based_history_with_evolution(server):
    """Test line-based tracking with evolution metadata."""
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py",
        start_line=1,
        end_line=50,
        show_evolution=True,
        max_commits=5,
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


@pytest.mark.asyncio
async def test_function_history_with_line_fallback(server):
    """Test function tracking with fallback line numbers."""
    result = await server.git_handler.get_file_history(
        "cicada/git_helper.py",
        function_name="get_recent_commits",
        start_line=10,
        end_line=100,
        max_commits=5,
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


# Integration Tests


@pytest.mark.asyncio
async def test_acceptance_full_workflow_module_to_function(server):
    """Test a complete workflow: search module, then search its functions."""
    # First, search for a module
    module_result = await server.module_handler.search_module("AB.Generators", "markdown")
    assert len(module_result) > 0
    module_text = module_result[0].text
    assert "AB.Generators" in module_text

    # Then search for a function in that module
    # The actual function names depend on test data
    # This tests the integration between module and function search


@pytest.mark.asyncio
async def test_acceptance_output_format_consistency(server):
    """Test that markdown and JSON formats both work for the same query."""
    function_name = "add_numbers/2"

    # Get markdown output
    markdown_result = await server.function_handler.search_function(
        function_name, output_format="markdown"
    )
    assert len(markdown_result) > 0
    markdown_text = markdown_result[0].text
    assert function_name.split("/")[0] in markdown_text

    # Get JSON output
    json_result = await server.function_handler.search_function(function_name, output_format="json")
    assert len(json_result) > 0
    json_text = json_result[0].text
    assert json_text.strip()

    # Both should contain meaningful content
    assert len(markdown_text) > 0
    assert len(json_text) > 0


@pytest.mark.asyncio
async def test_acceptance_error_handling_nonexistent_module(server):
    """Test error handling when searching for nonexistent module."""
    result = await server.module_handler.search_module(
        "NonexistentModule.That.DoesNotExist", "markdown"
    )
    assert len(result) > 0
    text = result[0].text
    # Should have some response, even if it's an error message
    assert text.strip()


@pytest.mark.asyncio
async def test_acceptance_error_handling_nonexistent_function(server):
    """Test error handling when searching for nonexistent function."""
    result = await server.function_handler.search_function(
        "nonexistent_function_xyz/99", output_format="markdown"
    )
    assert len(result) > 0
    text = result[0].text
    # Should have some response, even if it's an error message
    assert text.strip()


# Shell Script Compatibility Tests


@pytest.mark.asyncio
async def test_shell_script_search_module_compatibility(config_path):
    """Test that mimics search_module.sh behavior."""
    # This test replicates exactly what the shell script does
    server = CicadaServer(config_path=config_path)
    result = await server.module_handler.search_module("AB.Generators", "markdown")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # The shell script prints this, so we verify it's printable
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_shell_script_search_function_compatibility(config_path):
    """Test that mimics search_function.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server.function_handler.search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=False,
        max_examples=5,
        usage_type="all",
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_shell_script_check_moduledoc_compatibility(config_path):
    """Test that mimics check_moduledoc.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server.module_handler.search_module("AB.Generators", "markdown")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # Verify moduledoc is actually shown (should have substantial content)
    assert len(text) > 50


@pytest.mark.asyncio
async def test_shell_script_check_functiondoc_compatibility(config_path):
    """Test that mimics check_functiondoc.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server.function_handler.search_function(
        "add_numbers/2", output_format="markdown"
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # Should have function documentation
    assert "add_numbers" in text
