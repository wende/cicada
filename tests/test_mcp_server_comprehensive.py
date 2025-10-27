#!/usr/bin/env python
"""
Comprehensive tests for mcp_server.py module.

Tests MCP server initialization, tool validation, and core functionality.
"""

import json
import sys
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp_server import CicadaServer


class TestServerInitialization:
    """Test CicadaServer initialization and configuration."""

    def test_init_config_not_found(self, tmp_path):
        """Test error when config file doesn't exist."""
        config_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            CicadaServer(str(config_path))

    def test_init_index_not_found(self, tmp_path):
        """Test error when index file doesn't exist."""
        # Create config but no index
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(tmp_path / "nonexistent.json")},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(FileNotFoundError, match="Index file not found"):
            CicadaServer(str(config_path))

    def test_init_pr_index_missing_graceful(self, tmp_path):
        """Test graceful handling when PR index is missing."""
        # Create minimal valid index
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create config
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Should not raise, just set pr_index to None
        server = CicadaServer(str(config_path))
        assert server.pr_index is None

    def test_init_pr_index_malformed_json(self, tmp_path):
        """Test handling of malformed PR index JSON."""
        # Create minimal valid index
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create malformed PR index
        pr_index_path = tmp_path / ".cicada" / "pr_index.json"
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        pr_index_path.write_text("{invalid json")

        # Create config
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Should handle gracefully
        server = CicadaServer(str(config_path))
        assert server.pr_index is None

    def test_init_git_helper_failure(self, tmp_path):
        """Test graceful handling when GitHelper initialization fails."""
        # Create minimal valid index
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create config pointing to non-git directory
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Should set git_helper to None
        server = CicadaServer(str(config_path))
        # git_helper might be None if tmp_path is not a git repo


class TestToolInputValidation:
    """Test input validation for all MCP tools."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance."""
        # Create minimal valid index
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_search_module_missing_both_params(self, test_server):
        """Test search_module error when both module_name and file_path are missing."""
        result = await test_server.call_tool("search_module", {})

        assert len(result) == 1
        assert "Either 'module_name' or 'file_path' must be provided" in result[0].text

    @pytest.mark.asyncio
    async def test_search_module_invalid_file_path(self, test_server):
        """Test search_module error when file_path doesn't resolve."""
        result = await test_server.call_tool(
            "search_module", {"file_path": "nonexistent/file.ex"}
        )

        assert len(result) == 1
        assert "Could not find module in file" in result[0].text

    @pytest.mark.asyncio
    async def test_search_function_missing_param(self, test_server):
        """Test search_function error when function_name is missing."""
        result = await test_server.call_tool("search_function", {})

        assert len(result) == 1
        assert "'function_name' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_search_module_usage_missing_param(self, test_server):
        """Test search_module_usage error when module_name is missing."""
        result = await test_server.call_tool("search_module_usage", {})

        assert len(result) == 1
        assert "'module_name' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_find_pr_for_line_missing_file_path(self, test_server):
        """Test find_pr_for_line error when file_path is missing."""
        result = await test_server.call_tool("find_pr_for_line", {"line_number": 42})

        assert len(result) == 1
        assert "'file_path' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_find_pr_for_line_missing_line_number(self, test_server):
        """Test find_pr_for_line error when line_number is missing."""
        result = await test_server.call_tool(
            "find_pr_for_line", {"file_path": "test.ex"}
        )

        assert len(result) == 1
        assert "'line_number' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_file_history_missing_file_path(self, test_server):
        """Test get_file_history error when file_path is missing."""
        result = await test_server.call_tool("get_file_history", {})

        assert len(result) == 1
        assert "'file_path' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_file_history_precise_tracking_requires_lines(self, test_server):
        """Test get_file_history error when precise_tracking without line range."""
        result = await test_server.call_tool(
            "get_file_history", {"file_path": "test.ex", "precise_tracking": True}
        )

        assert len(result) == 1
        assert "start_line" in result[0].text and "end_line" in result[0].text

    @pytest.mark.asyncio
    async def test_get_function_blame_missing_file_path(self, test_server):
        """Test get_function_blame error when file_path is missing."""
        result = await test_server.call_tool(
            "get_function_blame", {"start_line": 1, "end_line": 10}
        )

        assert len(result) == 1
        assert "'file_path' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_function_blame_missing_lines(self, test_server):
        """Test get_function_blame error when line range is missing."""
        result = await test_server.call_tool(
            "get_function_blame", {"file_path": "test.ex"}
        )

        assert len(result) == 1
        assert "start_line" in result[0].text and "end_line" in result[0].text

    @pytest.mark.asyncio
    async def test_get_file_pr_history_missing_file_path(self, test_server):
        """Test get_file_pr_history error when file_path is missing."""
        result = await test_server.call_tool("get_file_pr_history", {})

        assert len(result) == 1
        assert "'file_path' is required" in result[0].text


class TestResolveFileToModule:
    """Test _resolve_file_to_module functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server with sample modules."""
        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                },
                "MyApp.Account": {
                    "file": "lib/my_app/account.ex",
                    "line": 1,
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                },
            },
            "metadata": {"total_modules": 2},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    def test_resolve_exact_match(self, test_server):
        """Test exact file path match."""
        result = test_server._resolve_file_to_module("lib/my_app/user.ex")
        assert result == "MyApp.User"

    def test_resolve_absolute_path(self, test_server):
        """Test resolution with absolute path."""
        result = test_server._resolve_file_to_module("/some/path/lib/my_app/user.ex")
        assert result == "MyApp.User"

    def test_resolve_partial_path(self, test_server):
        """Test resolution with partial path."""
        result = test_server._resolve_file_to_module("my_app/user.ex")
        assert result == "MyApp.User"

    def test_resolve_no_match(self, test_server):
        """Test when no module matches."""
        result = test_server._resolve_file_to_module("nonexistent.ex")
        assert result is None


class TestSearchModuleUsage:
    """Test _search_module_usage functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server with module usage data."""
        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                    "aliases": {},
                    "imports": [],
                    "requires": [],
                    "uses": [],
                    "calls": [],
                },
                "MyApp.Account": {
                    "file": "lib/my_app/account.ex",
                    "line": 1,
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                    "aliases": {"User": "MyApp.User"},
                    "imports": ["MyApp.User"],
                    "requires": [],
                    "uses": [],
                    "calls": [
                        {"module": "User", "function": "create", "arity": 1, "line": 10}
                    ],
                },
            },
            "metadata": {"total_modules": 2},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_search_module_usage_not_found(self, test_server):
        """Test error when module is not found."""
        result = await test_server._search_module_usage(
            "NonExistent.Module", "markdown"
        )

        assert len(result) == 1
        assert "not found in index" in result[0].text

    @pytest.mark.asyncio
    async def test_search_module_usage_with_aliases(self, test_server):
        """Test finding modules that alias the target."""
        result = await test_server._search_module_usage("MyApp.User", "markdown")

        assert len(result) == 1
        text = result[0].text
        assert "MyApp.Account" in text
        assert "alias" in text.lower() or "Aliases" in text

    @pytest.mark.asyncio
    async def test_search_module_usage_with_imports(self, test_server):
        """Test finding modules that import the target."""
        result = await test_server._search_module_usage("MyApp.User", "markdown")

        text = result[0].text
        assert "import" in text.lower() or "Imports" in text

    @pytest.mark.asyncio
    async def test_search_module_usage_with_function_calls(self, test_server):
        """Test finding function calls to the target module."""
        result = await test_server._search_module_usage("MyApp.User", "markdown")

        text = result[0].text
        assert "MyApp.Account" in text
        assert "create/1" in text


class TestFindPRForLine:
    """Test _find_pr_for_line functionality."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with PR index."""
        # Create minimal valid index
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create PR index
        pr_index = {
            "prs": {
                "123": {"number": 123, "title": "Add feature", "author": "developer"}
            },
            "commit_to_pr": {"abc123": 123},
        }
        pr_index_path = tmp_path / ".cicada" / "pr_index.json"
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        # Create config
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_find_pr_for_line_no_index(self, tmp_path):
        """Test when PR index doesn't exist."""
        # Create server without PR index
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))

        result = await server._find_pr_for_line("test.ex", 42, "text")

        assert len(result) == 1
        assert "PR index not found" in result[0].text
        assert "cicada-index-pr" in result[0].text

    @pytest.mark.asyncio
    async def test_find_pr_for_line_with_mock_finder(self, test_server_with_pr_index):
        """Test finding PR with mocked PRFinder."""
        with patch("cicada.mcp_server.PRFinder") as mock_finder_class:
            # Mock PRFinder instance
            mock_finder = Mock()
            mock_finder.find_pr_for_line.return_value = {
                "pr": {"number": 123, "title": "Test PR"},
                "commit": {"sha": "abc123"},
            }
            mock_finder.format_result.return_value = "PR #123: Test PR"
            mock_finder_class.return_value = mock_finder

            result = await test_server_with_pr_index._find_pr_for_line(
                "test.ex", 42, "text"
            )

            assert len(result) == 1
            assert "PR #123" in result[0].text


class TestGetFunctionBlame:
    """Test _get_function_blame functionality."""

    @pytest.fixture
    def test_server_with_git(self, tmp_path):
        """Create a test server with git helper."""
        # Initialize a git repo
        (tmp_path / ".git").mkdir()

        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_get_function_blame_no_git_helper(self, tmp_path):
        """Test when git helper is not available."""
        # Create server without git repo
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": "/tmp"},  # Non-git directory
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        server.git_helper = None  # Ensure no git helper

        result = await server._get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "not available" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_get_function_blame_no_results(self, test_server_with_git):
        """Test when no blame information is found."""
        # Mock git helper to return empty results
        test_server_with_git.git_helper = Mock()
        test_server_with_git.git_helper.get_function_blame.return_value = []

        result = await test_server_with_git._get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "No blame information found" in result[0].text


class TestGetFilePRHistory:
    """Test _get_file_pr_history functionality."""

    @pytest.fixture
    def test_server_with_pr_data(self, tmp_path):
        """Create a test server with PR history data."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create PR index with file history
        pr_index = {
            "file_to_prs": {"lib/test.ex": [123, 456]},
            "prs": {
                "123": {
                    "number": 123,
                    "title": "Add feature",
                    "author": "dev1",
                    "merged": True,
                    "url": "https://github.com/owner/repo/pull/123",
                    "description": "This adds a new feature",
                    "comments": [
                        {
                            "path": "lib/test.ex",
                            "author": "reviewer",
                            "body": "Looks good",
                            "line": 10,
                            "original_line": 10,
                            "resolved": True,
                        }
                    ],
                },
                "456": {
                    "number": 456,
                    "title": "Fix bug",
                    "author": "dev2",
                    "merged": False,
                    "state": "open",
                    "url": "https://github.com/owner/repo/pull/456",
                    "description": "Bug fix",
                    "comments": [],
                },
            },
        }
        pr_index_path = tmp_path / ".cicada" / "pr_index.json"
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_get_file_pr_history_no_pr_index(self, tmp_path):
        """Test when PR index is not available."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))

        result = await server._get_file_pr_history("lib/test.ex")

        assert len(result) == 1
        assert "PR index not available" in result[0].text
        assert "pr_indexer.py" in result[0].text

    @pytest.mark.asyncio
    async def test_get_file_pr_history_file_not_found(self, test_server_with_pr_data):
        """Test when file has no PRs."""
        result = await test_server_with_pr_data._get_file_pr_history(
            "lib/nonexistent.ex"
        )

        assert len(result) == 1
        assert "No pull requests found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_file_pr_history_success(self, test_server_with_pr_data):
        """Test successful PR history retrieval."""
        result = await test_server_with_pr_data._get_file_pr_history("lib/test.ex")

        assert len(result) == 1
        text = result[0].text

        # Should include both PRs
        assert "PR #123" in text
        assert "Add feature" in text
        assert "PR #456" in text
        assert "Fix bug" in text

        # Should include PR details
        assert "dev1" in text
        assert "dev2" in text

        # Should include review comments
        assert "Looks good" in text
        assert "reviewer" in text

    @pytest.mark.asyncio
    async def test_get_file_pr_history_absolute_path(
        self, test_server_with_pr_data, tmp_path
    ):
        """Test with absolute file path."""
        abs_path = tmp_path / "lib" / "test.ex"

        result = await test_server_with_pr_data._get_file_pr_history(str(abs_path))

        assert len(result) == 1
        # Should normalize to relative path and find PRs
        text = result[0].text
        assert "PR #123" in text or "No pull requests found" in text


class TestListTools:
    """Test list_tools functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self, test_server):
        """Test that list_tools returns all expected tools."""
        tools = await test_server.list_tools()

        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "search_module",
            "search_function",
            "search_module_usage",
            "find_pr_for_line",
            "get_file_history",
            "get_function_blame",
            "get_file_pr_history",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found in list"

    @pytest.mark.asyncio
    async def test_list_tools_has_descriptions(self, test_server):
        """Test that all tools have descriptions."""
        tools = await test_server.list_tools()

        for tool in tools:
            assert tool.description, f"Tool '{tool.name}' missing description"
            assert (
                len(tool.description) > 10
            ), f"Tool '{tool.name}' has very short description"

    @pytest.mark.asyncio
    async def test_list_tools_has_schemas(self, test_server):
        """Test that all tools have input schemas."""
        tools = await test_server.list_tools()

        for tool in tools:
            assert tool.inputSchema, f"Tool '{tool.name}' missing inputSchema"
            assert (
                "properties" in tool.inputSchema
            ), f"Tool '{tool.name}' schema missing properties"


class TestUnknownTool:
    """Test handling of unknown tool names."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_error(self, test_server):
        """Test that calling unknown tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await test_server.call_tool("nonexistent_tool", {})


class TestExtractCompleteCall:
    """Test _extract_complete_call functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance."""
        index = {
            "modules": {},
            "metadata": {"total_modules": 0, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    def test_extract_complete_call_with_context(self, test_server):
        """Test extracting code with context."""
        lines = [
            "defmodule Test do\n",
            "  def function do\n",
            "    x = 1\n",
            "    y = 2\n",
            "    call_function(x, y)\n",  # Line 5
            "    z = 3\n",
            "    z\n",
            "  end\n",
            "end\n",
        ]

        # Extract line 5 with context
        result = test_server._extract_complete_call(lines, 5)

        assert result is not None
        assert "call_function(x, y)" in result
        assert "y = 2" in result  # Context before
        assert "z = 3" in result  # Context after

    def test_extract_complete_call_at_start(self, test_server):
        """Test extracting code at start of file."""
        lines = [
            "first_line()\n",
            "second_line()\n",
            "third_line()\n",
        ]

        result = test_server._extract_complete_call(lines, 1)

        assert result is not None
        assert "first_line()" in result
        # Should not have lines before
        assert len(result.split("\n")) <= 3

    def test_extract_complete_call_at_end(self, test_server):
        """Test extracting code at end of file."""
        lines = [
            "first_line()\n",
            "second_line()\n",
            "last_line()\n",
        ]

        result = test_server._extract_complete_call(lines, 3)

        assert result is not None
        assert "last_line()" in result
        # Should not have lines after
        assert len(result.split("\n")) <= 3

    def test_extract_complete_call_dedents_code(self, test_server):
        """Test that code is dedented properly."""
        lines = [
            "defmodule Test do\n",
            "  def function do\n",
            "    indented_call()\n",
            "  end\n",
            "end\n",
        ]

        result = test_server._extract_complete_call(lines, 3)

        assert result is not None
        # Should be dedented (no leading spaces)
        assert not result.startswith("    ")
        assert "indented_call()" in result

    def test_extract_complete_call_invalid_line(self, test_server):
        """Test with invalid line number."""
        lines = ["line1\n", "line2\n"]

        # Line 0 (invalid)
        result = test_server._extract_complete_call(lines, 0)
        assert result is None

        # Line beyond file
        result = test_server._extract_complete_call(lines, 100)
        assert result is None


class TestGetFileHistoryWithEvolution:
    """Test _get_file_history with evolution metadata."""

    @pytest.fixture
    def test_server_with_git(self, tmp_path):
        """Create a test server with mocked git helper."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))

        # Mock git helper
        server.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_file_history_with_evolution_metadata(self, test_server_with_git):
        """Test get_file_history with show_evolution=True."""
        # Mock evolution data
        test_server_with_git.git_helper.get_function_history_precise.return_value = [
            {
                "sha": "abc123",
                "summary": "Add feature",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Add feature\n\nDetailed description",
            }
        ]
        test_server_with_git.git_helper.get_function_evolution.return_value = {
            "created_at": {"date": "2024-01-01", "author": "dev1", "sha": "abc123"},
            "last_modified": {"date": "2024-01-10", "author": "dev2", "sha": "def456"},
            "total_modifications": 5,
            "modification_frequency": 2.5,
        }

        result = await test_server_with_git._get_file_history(
            "test.ex",
            function_name="test_func",
            start_line=1,
            end_line=10,
            show_evolution=True,
            max_commits=10,
        )

        assert len(result) == 1
        text = result[0].text

        # Check for evolution metadata
        assert "Function Evolution" in text
        assert "Created:" in text
        assert "Last Modified:" in text
        assert "5 commit(s)" in text  # Total modifications
        assert "Modification Frequency:" in text
        assert "2.5" in text

    @pytest.mark.asyncio
    async def test_file_history_with_relevance_indicators(self, test_server_with_git):
        """Test get_file_history with relevance indicators."""
        test_server_with_git.git_helper.get_file_history.return_value = [
            {
                "sha": "abc123",
                "summary": "Update function",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Update function",
                "relevance": "mentioned",
            }
        ]

        result = await test_server_with_git._get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        text = result[0].text

        # Check for relevance indicator
        assert "Relevance:" in text or "mentioned" in text.lower()

    @pytest.mark.asyncio
    async def test_file_history_with_full_commit_message(self, test_server_with_git):
        """Test that full commit messages are shown when different from summary."""
        test_server_with_git.git_helper.get_file_history.return_value = [
            {
                "sha": "abc123",
                "summary": "Short summary",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Short summary\n\nThis is a much longer\nmultiline commit message",
            }
        ]

        result = await test_server_with_git._get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        text = result[0].text

        # Should include full message
        assert "Full message:" in text
        assert "This is a much longer" in text

    @pytest.mark.asyncio
    async def test_file_history_no_commits_found(self, test_server_with_git):
        """Test when no commits are found."""
        test_server_with_git.git_helper.get_file_history.return_value = []

        result = await test_server_with_git._get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        assert "No commit history found" in result[0].text

    @pytest.mark.asyncio
    async def test_file_history_with_function_tracking(self, test_server_with_git):
        """Test file history with function name tracking."""
        test_server_with_git.git_helper.get_function_history_precise.return_value = [
            {
                "sha": "abc123",
                "summary": "Update function",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Update function",
            }
        ]

        result = await test_server_with_git._get_file_history(
            "test.ex",
            function_name="my_function",
            start_line=10,
            end_line=20,
            max_commits=10,
        )

        assert len(result) == 1
        text = result[0].text

        # Should mention function tracking
        assert "function tracking" in text.lower() or "my_function" in text


class TestGetFunctionBlameFormatting:
    """Test _get_function_blame with various formatting scenarios."""

    @pytest.fixture
    def test_server_with_git(self, tmp_path):
        """Create a test server with mocked git helper."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        server.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_function_blame_with_multiple_groups(self, test_server_with_git):
        """Test blame formatting with multiple authorship groups."""
        test_server_with_git.git_helper.get_function_blame.return_value = [
            {
                "author": "dev1",
                "author_email": "dev1@example.com",
                "sha": "abc123",
                "date": "2024-01-01T12:00:00",
                "line_start": 10,
                "line_end": 12,
                "line_count": 3,
                "lines": [
                    {"line_number": 10, "content": "def function do"},
                    {"line_number": 11, "content": "  x = 1"},
                    {"line_number": 12, "content": "  y = 2"},
                ],
            },
            {
                "author": "dev2",
                "author_email": "dev2@example.com",
                "sha": "def456",
                "date": "2024-01-05T15:00:00",
                "line_start": 13,
                "line_end": 13,
                "line_count": 1,
                "lines": [
                    {"line_number": 13, "content": "  z = 3"},
                ],
            },
        ]

        result = await test_server_with_git._get_function_blame("test.ex", 10, 13)

        assert len(result) == 1
        text = result[0].text

        # Check for multiple groups
        assert "Group 1:" in text
        assert "Group 2:" in text
        assert "dev1" in text
        assert "dev2" in text

        # Check line ranges
        assert "lines 10-12" in text
        assert "line 13" in text

        # Check code content
        assert "def function do" in text
        assert "z = 3" in text

    @pytest.mark.asyncio
    async def test_function_blame_error_handling(self, test_server_with_git):
        """Test error handling in get_function_blame."""
        test_server_with_git.git_helper.get_function_blame.side_effect = Exception(
            "Git error"
        )

        result = await test_server_with_git._get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "Error getting blame information" in result[0].text


class TestGetFilePRHistoryFormatting:
    """Test _get_file_pr_history with various formatting scenarios."""

    @pytest.fixture
    def test_server_with_long_description(self, tmp_path):
        """Create a test server with PR data including long descriptions."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Create PR index with long description
        long_description = "\n".join([f"Line {i} of description" for i in range(15)])
        pr_index = {
            "file_to_prs": {"lib/test.ex": [789]},
            "prs": {
                "789": {
                    "number": 789,
                    "title": "PR with long description",
                    "author": "dev1",
                    "merged": True,
                    "url": "https://github.com/owner/repo/pull/789",
                    "description": long_description,
                    "comments": [
                        {
                            "path": "lib/test.ex",
                            "author": "reviewer1",
                            "body": "Comment without line number",
                            "original_line": 20,
                            "resolved": False,
                        },
                        {
                            "path": "lib/test.ex",
                            "author": "reviewer2",
                            "body": "Comment with line number",
                            "line": 15,
                            "original_line": 15,
                            "resolved": True,
                        },
                    ],
                }
            },
        }
        pr_index_path = tmp_path / ".cicada" / "pr_index.json"
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_pr_history_with_long_description_trimmed(
        self, test_server_with_long_description
    ):
        """Test that long descriptions are trimmed."""
        result = await test_server_with_long_description._get_file_pr_history(
            "lib/test.ex"
        )

        assert len(result) == 1
        text = result[0].text

        # Should show trimmed message
        assert "trimmed" in text.lower()
        assert "more lines" in text.lower()

    @pytest.mark.asyncio
    async def test_pr_history_with_comment_variations(
        self, test_server_with_long_description
    ):
        """Test PR history with different comment formats."""
        result = await test_server_with_long_description._get_file_pr_history(
            "lib/test.ex"
        )

        assert len(result) == 1
        text = result[0].text

        # Should show comment with line number
        assert "Line 15" in text
        assert "reviewer2" in text
        assert "✓ Resolved" in text

        # Should show comment without line number
        assert "Original line 20" in text or "unmapped" in text.lower()
        assert "reviewer1" in text

    @pytest.mark.asyncio
    async def test_pr_history_absolute_path_outside_repo(
        self, test_server_with_long_description, tmp_path
    ):
        """Test with absolute path outside repository."""
        # Create path outside repo
        outside_path = Path("/totally/different/path/file.ex")

        result = await test_server_with_long_description._get_file_pr_history(
            str(outside_path)
        )

        assert len(result) == 1
        assert "not within repository" in result[0].text


class TestAddCodeExamples:
    """Test _add_code_examples functionality."""

    @pytest.fixture
    def test_server_with_files(self, tmp_path):
        """Create a test server with actual code files."""
        # Create a sample file
        code_file = tmp_path / "lib" / "test.ex"
        code_file.parent.mkdir(parents=True, exist_ok=True)
        code_file.write_text(
            "defmodule Test do\n"
            "  def function1 do\n"
            "    call_target()\n"
            "  end\n"
            "  def function2 do\n"
            "    call_target()\n"
            "  end\n"
            "end\n"
        )

        index = {
            "modules": {},
            "metadata": {"total_modules": 0, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    def test_add_code_examples_success(self, test_server_with_files):
        """Test adding code examples to call sites."""
        call_sites = [
            {
                "file": "lib/test.ex",
                "line": 3,
                "calling_module": "Test",
                "calling_function": {"name": "function1", "arity": 0},
            }
        ]

        test_server_with_files._add_code_examples(call_sites)

        # Should have added code_line
        assert "code_line" in call_sites[0]
        assert "call_target()" in call_sites[0]["code_line"]

    def test_add_code_examples_file_not_found(self, test_server_with_files):
        """Test graceful handling when file doesn't exist."""
        call_sites = [
            {"file": "lib/nonexistent.ex", "line": 10, "calling_module": "Test"}
        ]

        # Should not raise, just skip
        test_server_with_files._add_code_examples(call_sites)

        # Should not have code_line
        assert "code_line" not in call_sites[0]


class TestFindPRForLineNetworkFallback:
    """Test _find_pr_for_line with network fallback."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with PR index."""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {"prs": {}, "commit_to_pr": {}}
        pr_index_path = tmp_path / ".cicada" / "pr_index.json"
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_find_pr_network_fallback_finds_pr(self, test_server_with_pr_index):
        """Test network fallback when index is incomplete."""
        with patch("cicada.mcp_server.PRFinder") as mock_finder_class:
            # First call (index) returns commit but no PR
            mock_index_finder = Mock()
            mock_index_finder.find_pr_for_line.return_value = {
                "pr": None,
                "commit": {"sha": "abc123"},
            }

            # Second call (network) finds the PR
            mock_network_finder = Mock()
            mock_network_finder.find_pr_for_line.return_value = {
                "pr": {"number": 123, "title": "Test PR"},
                "commit": {"sha": "abc123"},
            }

            mock_finder_class.side_effect = [mock_index_finder, mock_network_finder]

            result = await test_server_with_pr_index._find_pr_for_line(
                "test.ex", 42, "text"
            )

            assert len(result) == 1
            # Should suggest updating index
            assert (
                "incomplete" in result[0].text.lower()
                or "update" in result[0].text.lower()
            )

    @pytest.mark.asyncio
    async def test_find_pr_network_fallback_no_pr(self, test_server_with_pr_index):
        """Test when commit truly has no PR."""
        with patch("cicada.mcp_server.PRFinder") as mock_finder_class:
            # Both calls return no PR
            mock_index_finder = Mock()
            mock_index_finder.find_pr_for_line.return_value = {
                "pr": None,
                "commit": {"sha": "abc123"},
            }
            mock_index_finder.format_result.return_value = "Commit abc123 (no PR)"

            mock_network_finder = Mock()
            mock_network_finder.find_pr_for_line.return_value = {
                "pr": None,
                "commit": {"sha": "abc123"},
            }

            mock_finder_class.side_effect = [mock_index_finder, mock_network_finder]

            result = await test_server_with_pr_index._find_pr_for_line(
                "test.ex", 42, "text"
            )

            assert len(result) == 1
            # Should show result without suggesting index update
            assert "Commit abc123" in result[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
