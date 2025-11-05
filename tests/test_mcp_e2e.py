#!/usr/bin/env python
"""
End-to-End Tests for MCP Server

This test suite validates complete user workflows and tool interactions
in real-world scenarios, testing the MCP server as users would actually use it.

Test Categories:
1. Complete Workflow Tests - Multi-step user scenarios
2. Tool Integration Tests - How tools work together
3. Real Repository Tests - Tests on actual Elixir code
4. Concurrent Request Tests - Async behavior validation
5. Error Recovery Tests - Resilience under failure conditions
6. Performance Tests - Large data handling
"""

import json
import pytest
import yaml
from cicada.mcp.server import CicadaServer
from mcp.types import TextContent


@pytest.fixture
def sample_elixir_repo(tmp_path):
    """Create a sample Elixir repository structure with realistic code."""
    repo = tmp_path / "sample_app"
    repo.mkdir()

    # Create mix.exs
    (repo / "mix.exs").write_text(
        """
defmodule SampleApp.MixProject do
  use Mix.Project

  def project do
    [
      app: :sample_app,
      version: "0.1.0"
    ]
  end
end
"""
    )

    # Create lib directory structure
    lib = repo / "lib"
    lib.mkdir()

    # Create User module
    (lib / "user.ex").write_text(
        """
defmodule SampleApp.User do
  @moduledoc \"\"\"
  User management module for handling user authentication and authorization.
  Provides functions for creating, updating, and validating users.
  \"\"\"

  @doc \"\"\"
  Creates a new user with the given attributes.
  Returns {:ok, user} on success or {:error, reason} on failure.
  \"\"\"
  def create_user(attrs) do
    # Implementation
    {:ok, attrs}
  end

  @doc \"\"\"
  Updates an existing user.
  \"\"\"
  def update_user(user, attrs) do
    # Implementation
    {:ok, Map.merge(user, attrs)}
  end

  @doc \"\"\"
  Validates user credentials.
  \"\"\"
  def validate_credentials(email, password) do
    # Implementation
    {:ok, %{email: email}}
  end

  defp hash_password(password) do
    # Private function
    :crypto.hash(:sha256, password)
  end
end
"""
    )

    # Create UserController module that uses User
    (lib / "user_controller.ex").write_text(
        """
defmodule SampleApp.UserController do
  @moduledoc \"\"\"
  Web controller for user-related actions.
  Handles HTTP requests for user management.
  \"\"\"

  alias SampleApp.User

  def create(conn, params) do
    case User.create_user(params) do
      {:ok, user} -> {:ok, user}
      {:error, reason} -> {:error, reason}
    end
  end

  def update(conn, params) do
    user = get_user(conn)
    User.update_user(user, params)
  end

  defp get_user(conn) do
    # Implementation
    %{}
  end
end
"""
    )

    # Create Auth module
    (lib / "auth.ex").write_text(
        """
defmodule SampleApp.Auth do
  @moduledoc \"\"\"
  Authentication helpers for verifying user identity.
  \"\"\"

  alias SampleApp.User

  def authenticate(email, password) do
    User.validate_credentials(email, password)
  end
end
"""
    )

    # Create test directory
    test_dir = repo / "test"
    test_dir.mkdir()

    (test_dir / "user_test.exs").write_text(
        """
defmodule SampleApp.UserTest do
  use ExUnit.Case
  alias SampleApp.User

  test "creates a user" do
    assert {:ok, _user} = User.create_user(%{name: "Test"})
  end

  test "validates credentials" do
    assert {:ok, _} = User.validate_credentials("test@example.com", "password")
  end
end
"""
    )

    yield repo


@pytest.fixture
def e2e_server(sample_elixir_repo, tmp_path):
    """Create a fully initialized server with indexed repository."""
    from cicada.indexer import ElixirIndexer

    # Index the repository
    indexer = ElixirIndexer(verbose=False)
    index_path = tmp_path / "index.json"
    index_result = indexer.index_repository(str(sample_elixir_repo), str(index_path))

    # Validate indexing succeeded
    assert index_result is not None, "Failed to index repository"
    assert index_result.get("metadata", {}).get("total_modules", 0) > 0, "No modules were indexed"

    # Create config
    config = {
        "repository": {"path": str(sample_elixir_repo)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return CicadaServer(str(config_path))


class TestCompleteWorkflows:
    """Test complete user workflows spanning multiple tool calls."""

    @pytest.mark.asyncio
    async def test_explore_module_then_find_usages_workflow(self, e2e_server):
        """
        Workflow: User wants to understand a module and see where it's used.
        Steps:
        1. Search for User module
        2. Find where User module is used
        3. Search for specific function create_user
        """
        # Step 1: Search for User module
        result = await e2e_server.call_tool(
            "search_module", {"module_name": "SampleApp.User", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "SampleApp.User" in text
        assert "create_user" in text
        assert "User management module" in text

        # Step 2: Find where User module is used
        result = await e2e_server.call_tool(
            "search_module_usage",
            {"module_name": "SampleApp.User", "format": "markdown"},
        )

        assert len(result) == 1
        text = result[0].text
        # Should find usage in UserController and Auth
        assert "UserController" in text or "Auth" in text

        # Step 3: Search for specific function
        result = await e2e_server.call_tool(
            "search_function", {"function_name": "create_user", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "create_user" in text
        assert "SampleApp.User" in text

    @pytest.mark.asyncio
    async def test_find_function_and_get_call_examples_workflow(self, e2e_server):
        """
        Workflow: User wants to find a function and see how it's called.
        Steps:
        1. Search for function with usage examples
        2. Verify call sites are included
        """
        result = await e2e_server.call_tool(
            "search_function",
            {
                "function_name": "create_user",
                "include_usage_examples": True,
                "max_examples": 3,
                "format": "markdown",
            },
        )

        assert len(result) == 1
        text = result[0].text
        assert "create_user" in text
        assert "SampleApp.User" in text
        # Should include call sites from UserController or tests
        assert "UserController" in text or "Test" in text.lower()

    @pytest.mark.asyncio
    async def test_search_module_by_file_path_workflow(self, e2e_server):
        """
        Workflow: User has a file path and wants to explore the module.
        Steps:
        1. Search module by file path
        2. Verify module is resolved correctly
        """
        result = await e2e_server.call_tool(
            "search_module", {"file_path": "lib/user.ex", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "SampleApp.User" in text
        assert "create_user" in text

    @pytest.mark.asyncio
    async def test_filter_private_functions_workflow(self, e2e_server):
        """
        Workflow: User wants to see only public API of a module.
        Steps:
        1. Search module with private functions excluded
        2. Verify private functions are not shown
        """
        # Get module with private functions excluded (default)
        result = await e2e_server.call_tool(
            "search_module",
            {
                "module_name": "SampleApp.User",
                "private_functions": "exclude",
                "format": "markdown",
            },
        )

        assert len(result) == 1
        text = result[0].text
        assert "create_user" in text  # Public function
        assert "hash_password" not in text  # Private function

    @pytest.mark.asyncio
    async def test_search_qualified_function_workflow(self, e2e_server):
        """
        Workflow: User searches for function with module prefix.
        Steps:
        1. Search for Module.function format
        2. Verify only that module's function is returned
        """
        result = await e2e_server.call_tool(
            "search_function",
            {"function_name": "SampleApp.User.create_user", "format": "markdown"},
        )

        assert len(result) == 1
        text = result[0].text
        assert "SampleApp.User" in text
        assert "create_user" in text


class TestToolIntegration:
    """Test how different tools work together."""

    @pytest.mark.asyncio
    async def test_search_function_in_tests_only(self, e2e_server):
        """Test filtering function calls to show only test usage."""
        result = await e2e_server.call_tool(
            "search_function",
            {
                "function_name": "create_user",
                "test_files_only": True,
                "format": "markdown",
            },
        )

        assert len(result) == 1
        text = result[0].text
        # Should only show calls from test files
        if "call" in text.lower():
            assert "test" in text.lower()

    @pytest.mark.asyncio
    async def test_list_all_available_tools(self, e2e_server):
        """Verify all expected tools are available."""
        tools = await e2e_server.list_tools()

        tool_names = [tool.name for tool in tools]

        # Verify core search tools
        assert "search_module" in tool_names
        assert "search_function" in tool_names
        assert "search_module_usage" in tool_names

        # Verify git tools
        assert "get_commit_history" in tool_names
        assert "get_blame" in tool_names
        assert "find_pr_for_line" in tool_names

        # Verify analysis tools
        assert "search_by_features" in tool_names
        assert "find_dead_code" in tool_names
        assert "get_file_pr_history" in tool_names

    @pytest.mark.asyncio
    async def test_json_output_format(self, e2e_server):
        """Test JSON output format for all tools that support it."""
        # Test search_module with JSON
        result = await e2e_server.call_tool(
            "search_module", {"module_name": "SampleApp.User", "format": "json"}
        )

        assert len(result) == 1
        text = result[0].text
        # Verify it's valid JSON
        data = json.loads(text)
        assert "module" in data
        assert data["module"] == "SampleApp.User"

    @pytest.mark.asyncio
    async def test_markdown_output_format(self, e2e_server):
        """Test markdown output format consistency."""
        result = await e2e_server.call_tool(
            "search_module", {"module_name": "SampleApp.User", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        # Check for markdown-like formatting
        # Note: The formatter may not use markdown headers, but should have structured text
        assert len(text) > 0
        assert "SampleApp.User" in text


class TestConcurrentRequests:
    """Test server behavior with concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_module_searches(self, e2e_server):
        """Test multiple concurrent module searches."""
        import asyncio

        # Create multiple concurrent requests
        tasks = [
            e2e_server.call_tool(
                "search_module", {"module_name": "SampleApp.User", "format": "markdown"}
            ),
            e2e_server.call_tool(
                "search_module",
                {"module_name": "SampleApp.UserController", "format": "markdown"},
            ),
            e2e_server.call_tool(
                "search_module", {"module_name": "SampleApp.Auth", "format": "markdown"}
            ),
        ]

        results = await asyncio.gather(*tasks)

        # Verify all requests completed successfully
        assert len(results) == 3
        for result in results:
            assert len(result) == 1
            assert isinstance(result[0], TextContent)

        # Verify each result is unique and contains expected module
        assert "SampleApp.User" in results[0][0].text
        assert "UserController" in results[1][0].text
        assert "Auth" in results[2][0].text

    @pytest.mark.asyncio
    async def test_concurrent_mixed_tool_calls(self, e2e_server):
        """Test concurrent calls to different tools."""
        import asyncio

        tasks = [
            e2e_server.call_tool(
                "search_module", {"module_name": "SampleApp.User", "format": "markdown"}
            ),
            e2e_server.call_tool(
                "search_function",
                {"function_name": "create_user", "format": "markdown"},
            ),
            e2e_server.call_tool(
                "search_module_usage",
                {"module_name": "SampleApp.User", "format": "markdown"},
            ),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert len(result) == 1

        # Verify each tool returned correct data
        assert "SampleApp.User" in results[0][0].text, "Module search should find User"
        assert "create_user" in results[1][0].text, "Function search should find create_user"
        assert (
            "usage" in results[2][0].text.lower() or "used" in results[2][0].text.lower()
        ), "Module usage should report usage information"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_search_nonexistent_module(self, e2e_server):
        """Test searching for a module that doesn't exist."""
        result = await e2e_server.call_tool(
            "search_module", {"module_name": "NonExistent.Module", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "not found" in text.lower() or "error" in text.lower()

    @pytest.mark.asyncio
    async def test_search_function_with_invalid_arity(self, e2e_server):
        """Test searching for function with non-existent arity."""
        result = await e2e_server.call_tool(
            "search_function",
            {"function_name": "create_user/999", "format": "markdown"},
        )

        assert len(result) == 1
        text = result[0].text
        # Should return no results or appropriate message
        assert "create_user" in text

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, e2e_server):
        """Test calling a non-existent tool."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await e2e_server.call_tool("nonexistent_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, e2e_server):
        """Test tool calls with missing required parameters."""
        # search_function requires function_name
        result = await e2e_server.call_tool("search_function", {})

        assert len(result) == 1
        text = result[0].text
        assert "required" in text.lower() or "error" in text.lower()

    @pytest.mark.asyncio
    async def test_search_module_without_identifiers(self, e2e_server):
        """Test search_module when neither module_name nor file_path is provided."""
        result = await e2e_server.call_tool("search_module", {})

        assert len(result) == 1
        text = result[0].text
        assert "must be provided" in text.lower()

    @pytest.mark.asyncio
    async def test_invalid_file_path(self, e2e_server):
        """Test search_module with invalid file path."""
        result = await e2e_server.call_tool(
            "search_module", {"file_path": "nonexistent/file.ex", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "could not find" in text.lower() or "not found" in text.lower()


class TestKeywordSearch:
    """Test keyword search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_features_without_index(self, e2e_server):
        """Test keyword search when keywords are not indexed."""
        result = await e2e_server.call_tool(
            "search_by_features", {"keywords": ["authentication", "user"]}
        )

        assert len(result) == 1
        text = result[0].text
        # Should return meaningful response about missing keywords or search results
        assert text, "Response should not be empty"
        assert (
            len(text) > 20
        ), "Response too short to be meaningful (should explain missing keywords or provide results)"

    @pytest.mark.asyncio
    async def test_search_by_features_invalid_input(self, e2e_server):
        """Test keyword search with invalid input."""
        result = await e2e_server.call_tool("search_by_features", {"keywords": "not_a_list"})

        assert len(result) == 1
        text = result[0].text
        assert "must be a list" in text.lower()

    @pytest.mark.asyncio
    async def test_search_by_features_empty_list(self, e2e_server):
        """Test keyword search with empty keywords list."""
        result = await e2e_server.call_tool("search_by_features", {"keywords": []})

        assert len(result) == 1
        text = result[0].text
        assert "required" in text.lower()

    @pytest.mark.asyncio
    async def test_search_by_features_invalid_filter_type(self, e2e_server):
        """Test keyword search with invalid filter_type parameter."""
        result = await e2e_server.call_tool(
            "search_by_features",
            {"keywords": ["test"], "filter_type": "invalid_type"},
        )

        assert len(result) == 1
        text = result[0].text
        assert "filter_type" in text.lower()
        assert "all" in text.lower()

    @pytest.mark.asyncio
    async def test_search_by_features_filter_modules(self, e2e_server):
        """Test keyword search with modules-only filter."""
        result = await e2e_server.call_tool(
            "search_by_features",
            {"keywords": ["authentication", "user"], "filter_type": "modules"},
        )

        assert len(result) == 1
        text = result[0].text
        assert text, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_search_by_features_filter_functions(self, e2e_server):
        """Test keyword search with functions-only filter."""
        result = await e2e_server.call_tool(
            "search_by_features",
            {"keywords": ["authentication", "user"], "filter_type": "functions"},
        )

        assert len(result) == 1
        text = result[0].text
        assert text, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_search_by_features_filter_all(self, e2e_server):
        """Test keyword search with all-types filter (default)."""
        result = await e2e_server.call_tool(
            "search_by_features",
            {"keywords": ["authentication", "user"], "filter_type": "all"},
        )

        assert len(result) == 1
        text = result[0].text
        assert text, "Response should not be empty"


class TestDeadCodeAnalysis:
    """Test dead code detection functionality."""

    @pytest.mark.asyncio
    async def test_find_dead_code_high_confidence(self, e2e_server):
        """Test finding dead code with high confidence."""
        result = await e2e_server.call_tool(
            "find_dead_code", {"min_confidence": "high", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        # Should return analysis results or message
        assert text

    @pytest.mark.asyncio
    async def test_find_dead_code_all_confidence_levels(self, e2e_server):
        """Test dead code analysis with different confidence levels."""
        for confidence in ["high", "medium", "low"]:
            result = await e2e_server.call_tool(
                "find_dead_code", {"min_confidence": confidence, "format": "markdown"}
            )

            assert len(result) == 1
            assert result[0].text

    @pytest.mark.asyncio
    async def test_find_dead_code_json_format(self, e2e_server):
        """Test dead code analysis with JSON output."""
        result = await e2e_server.call_tool(
            "find_dead_code", {"min_confidence": "high", "format": "json"}
        )

        assert len(result) == 1
        text = result[0].text
        # Should be valid JSON
        try:
            data = json.loads(text)
            assert isinstance(data, (dict, list))
        except json.JSONDecodeError:
            pytest.fail("Dead code output is not valid JSON")


class TestModuleResolution:
    """Test module and file path resolution edge cases."""

    @pytest.mark.asyncio
    async def test_resolve_relative_file_path(self, e2e_server):
        """Test resolving relative file paths."""
        result = await e2e_server.call_tool(
            "search_module", {"file_path": "./lib/user.ex", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "SampleApp.User" in text

    @pytest.mark.asyncio
    async def test_resolve_file_path_without_lib_prefix(self, e2e_server):
        """Test resolving file paths without lib/ prefix."""
        result = await e2e_server.call_tool(
            "search_module", {"file_path": "user.ex", "format": "markdown"}
        )

        assert len(result) == 1
        text = result[0].text
        # Should either successfully resolve to module or return clear error message
        assert (
            "SampleApp.User" in text or "not found" in text.lower()
        ), "Should either resolve module or explain failure"


class TestRobustness:
    """Test server robustness under various conditions."""

    @pytest.mark.asyncio
    async def test_server_survives_multiple_errors(self, e2e_server):
        """Test that server continues functioning after errors."""
        # Make several invalid requests
        await e2e_server.call_tool("search_module", {})
        await e2e_server.call_tool("search_function", {})

        # Server should still work for valid requests
        result = await e2e_server.call_tool(
            "search_module", {"module_name": "SampleApp.User", "format": "markdown"}
        )

        assert len(result) == 1
        assert "SampleApp.User" in result[0].text

    @pytest.mark.asyncio
    async def test_large_result_handling(self, e2e_server):
        """Test handling of large result sets."""
        # Search for common function name that might return many results
        result = await e2e_server.call_tool(
            "search_function",
            {
                "function_name": "create_user",
                "include_usage_examples": True,
                "max_examples": 100,
                "format": "markdown",
            },
        )

        assert len(result) == 1
        assert result[0].text


class TestOutputConsistency:
    """Test output format consistency across tools."""

    @pytest.mark.asyncio
    async def test_all_tools_return_text_content(self, e2e_server):
        """Verify all tools return TextContent objects."""
        test_calls = [
            ("search_module", {"module_name": "SampleApp.User"}),
            ("search_function", {"function_name": "create_user"}),
            ("search_module_usage", {"module_name": "SampleApp.User"}),
        ]

        for tool_name, args in test_calls:
            result = await e2e_server.call_tool(tool_name, args)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert isinstance(result[0].text, str)
            assert len(result[0].text) > 0

    @pytest.mark.asyncio
    async def test_error_messages_are_user_friendly(self, e2e_server):
        """Test that error messages are clear and actionable."""
        # Test missing parameter error
        result = await e2e_server.call_tool("search_function", {})
        text = result[0].text

        # Should contain helpful information
        assert "required" in text.lower()
        assert len(text) > 10  # Not just a cryptic error code


class TestSpecialCases:
    """Test special cases and edge conditions."""

    @pytest.mark.asyncio
    async def test_module_with_no_functions(self, tmp_path):
        """Test module that has no functions defined."""
        # Create a minimal module
        repo = tmp_path / "minimal"
        repo.mkdir()
        (repo / "mix.exs").write_text("defmodule Minimal.MixProject do\nend")

        lib = repo / "lib"
        lib.mkdir()
        (lib / "empty.ex").write_text(
            """
defmodule Minimal.Empty do
  @moduledoc "Module with no functions"
end
"""
        )

        # Create server
        index_path = tmp_path / "empty_index.json"

        # Index it
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=False)
        index_result = indexer.index_repository(str(repo), str(index_path))

        # Validate indexing succeeded
        assert index_result is not None, "Failed to index repository"
        assert (
            index_result.get("metadata", {}).get("total_modules", 0) > 0
        ), "No modules were indexed"

        config = {
            "repository": {"path": str(repo)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "empty_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))

        result = await server.call_tool("search_module", {"module_name": "Minimal.Empty"})

        assert len(result) == 1
        text = result[0].text
        assert "Minimal.Empty" in text

    @pytest.mark.asyncio
    async def test_function_with_arity_zero(self, e2e_server):
        """Test searching for functions with arity 0."""
        # Add a module with arity-0 function
        result = await e2e_server.call_tool("search_function", {"function_name": "create_user/0"})

        assert len(result) == 1
        # Should handle gracefully even if not found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
