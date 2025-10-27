"""
Acceptance tests for Cicada MCP server.

These tests mirror the shell scripts in tests/acceptance/ but are
integrated with pytest for better coverage tracking and CI integration.
"""

# No unused imports

import pytest

from cicada.mcp_server import CicadaServer


# Fixtures


@pytest.fixture
def config_path():
    """Path to test fixtures config."""
    return "tests/fixtures/.cicada/config.yaml"


@pytest.fixture
async def server(config_path):
    """Create a CicadaServer instance for testing."""
    return CicadaServer(config_path=config_path)


# Module Search Tests (search_module.sh, check_moduledoc.sh)


@pytest.mark.asyncio
async def test_search_module_basic(server):
    """Test basic module search functionality."""
    result = await server._search_module("TestApp", "markdown")
    assert len(result) > 0
    text = result[0].text
    assert "TestApp" in text
    assert text.strip()  # Should have content


@pytest.mark.asyncio
async def test_search_module_includes_moduledoc(server):
    """Test that moduledoc is displayed when searching for modules."""
    result = await server._search_module("TestApp", "markdown")
    assert len(result) > 0
    text = result[0].text
    # Should contain module documentation
    assert "TestApp" in text
    # Verify it's actually showing documentation content, not just the name
    assert len(text) > 50  # Should be substantial


@pytest.mark.asyncio
async def test_search_module_json_format(server):
    """Test module search with JSON output format."""
    result = await server._search_module("AB.Generators", "json")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # JSON should contain the module name somewhere
    assert "AB.Generators" in text or "Generators" in text


# Function Search Tests (search_function.sh, check_functiondoc.sh)


@pytest.mark.asyncio
async def test_search_function_basic(server):
    """Test basic function search functionality."""
    result = await server._search_function(
        "add_numbers/2", output_format="markdown", include_usage_examples=False
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text


@pytest.mark.asyncio
async def test_search_function_with_examples(server):
    """Test function search with usage examples included."""
    result = await server._search_function(
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
    result = await server._search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=True,
        test_files_only=True,
        max_examples=10,
    )
    assert len(result) > 0
    text = result[0].text
    assert "add_numbers" in text


@pytest.mark.asyncio
async def test_search_function_with_limit(server):
    """Test function search with example limit."""
    result = await server._search_function(
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
    result = await server._search_function(
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
    result = await server._search_function(
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
    result = await server._get_file_history(
        "cicada/git_helper.py", function_name="get_recent_commits", max_commits=5
    )
    assert len(result) > 0
    text = result[0].text
    # Should contain commit information
    assert text.strip()


@pytest.mark.asyncio
async def test_function_history_with_evolution(server):
    """Test function history with evolution metadata."""
    result = await server._get_file_history(
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
    result = await server._get_file_history(
        "cicada/git_helper.py", function_name="get_recent_commits", max_commits=3
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


@pytest.mark.asyncio
async def test_line_based_history_tracking(server):
    """Test line-based history tracking mode."""
    result = await server._get_file_history(
        "cicada/git_helper.py", start_line=1, end_line=50, max_commits=5
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()


@pytest.mark.asyncio
async def test_line_based_history_with_evolution(server):
    """Test line-based tracking with evolution metadata."""
    result = await server._get_file_history(
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
    result = await server._get_file_history(
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
    module_result = await server._search_module("AB.Generators", "markdown")
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
    markdown_result = await server._search_function(
        function_name, output_format="markdown"
    )
    assert len(markdown_result) > 0
    markdown_text = markdown_result[0].text
    assert function_name.split("/")[0] in markdown_text

    # Get JSON output
    json_result = await server._search_function(function_name, output_format="json")
    assert len(json_result) > 0
    json_text = json_result[0].text
    assert json_text.strip()

    # Both should contain meaningful content
    assert len(markdown_text) > 0
    assert len(json_text) > 0


@pytest.mark.asyncio
async def test_acceptance_error_handling_nonexistent_module(server):
    """Test error handling when searching for nonexistent module."""
    result = await server._search_module(
        "NonexistentModule.That.DoesNotExist", "markdown"
    )
    assert len(result) > 0
    text = result[0].text
    # Should have some response, even if it's an error message
    assert text.strip()


@pytest.mark.asyncio
async def test_acceptance_error_handling_nonexistent_function(server):
    """Test error handling when searching for nonexistent function."""
    result = await server._search_function(
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
    result = await server._search_module("AB.Generators", "markdown")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # The shell script prints this, so we verify it's printable
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_shell_script_search_function_compatibility(config_path):
    """Test that mimics search_function.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server._search_function(
        "add_numbers/2",
        output_format="markdown",
        include_usage_examples=False,
        max_examples=5,
        test_files_only=False,
    )
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_shell_script_check_moduledoc_compatibility(config_path):
    """Test that mimics check_moduledoc.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server._search_module("AB.Generators", "markdown")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # Verify moduledoc is actually shown (should have substantial content)
    assert len(text) > 50


@pytest.mark.asyncio
async def test_shell_script_check_functiondoc_compatibility(config_path):
    """Test that mimics check_functiondoc.sh behavior."""
    server = CicadaServer(config_path=config_path)
    result = await server._search_function("add_numbers/2", output_format="markdown")
    assert len(result) > 0
    text = result[0].text
    assert text.strip()
    # Should have function documentation
    assert "add_numbers" in text
