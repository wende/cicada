#!/usr/bin/env python
"""
Tests for MCP server core functionality.

Tests server initialization, tool validation, and basic operations.
"""

import json

import pytest
import yaml

from cicada.mcp.server import CicadaServer


class TestServerInitialization:
    """Test CicadaServer initialization and configuration."""

    def test_init_config_not_found(self, tmp_path):
        """Should raise FileNotFoundError when config doesn't exist"""
        config_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            CicadaServer(str(config_path))

    def test_init_index_not_found(self, tmp_path):
        """Should raise FileNotFoundError when index doesn't exist"""
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(tmp_path / "nonexistent.json")},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(FileNotFoundError, match="Index file not found"):
            CicadaServer(str(config_path))

    @pytest.mark.parametrize("pr_index_content", [None, "{invalid json"])
    def test_pr_index_graceful_handling(self, pr_index_content, tmp_path):
        """Should handle missing or malformed PR index gracefully"""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        if pr_index_content is not None:
            pr_index_path = tmp_path / ".cicada" / "pr_index.json"
            pr_index_path.parent.mkdir(parents=True, exist_ok=True)
            pr_index_path.write_text(pr_index_content)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        assert server.pr_index is None


class TestToolInputValidation:
    """Test input validation for all MCP tools."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance"""
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
    @pytest.mark.parametrize(
        "tool,args,expected_error",
        [
            (
                "search_module",
                {},
                "Either 'module_name' or 'file_path' must be provided",
            ),
            ("search_function", {}, "'function_name' is required"),
            ("search_module_usage", {}, "'module_name' is required"),
            ("find_pr_for_line", {"line_number": 42}, "'file_path' is required"),
            ("find_pr_for_line", {"file_path": "test.ex"}, "'line_number' is required"),
            ("get_commit_history", {}, "'file_path' is required"),
            ("get_blame", {"start_line": 1, "end_line": 10}, "'file_path' is required"),
            ("get_blame", {"file_path": "test.ex"}, "start_line"),
            ("get_file_pr_history", {}, "'file_path' is required"),
        ],
    )
    async def test_tool_validation(self, tool, args, expected_error, test_server):
        """Should validate required parameters for all tools"""
        result = await test_server.call_tool(tool, args)
        assert len(result) == 1
        assert expected_error in result[0].text

    @pytest.mark.asyncio
    async def test_precise_tracking_requires_lines(self, test_server):
        """Should require line range when precise_tracking is enabled"""
        result = await test_server.call_tool(
            "get_commit_history", {"file_path": "test.ex", "precise_tracking": True}
        )
        assert len(result) == 1
        assert "start_line" in result[0].text and "end_line" in result[0].text


class TestResolveFileToModule:
    """Test _resolve_file_to_module functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server with sample modules"""
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

    @pytest.mark.parametrize(
        "file_path,expected",
        [
            ("lib/my_app/user.ex", "MyApp.User"),  # Exact match
            ("/some/path/lib/my_app/user.ex", "MyApp.User"),  # Absolute path
            ("my_app/user.ex", "MyApp.User"),  # Partial path
            ("nonexistent.ex", None),  # No match
        ],
    )
    def test_resolve_file_to_module(self, file_path, expected, test_server):
        """Should resolve file paths to module names"""
        result = test_server._resolve_file_to_module(file_path)
        assert result == expected


class TestSearchModuleUsage:
    """Test _search_module_usage functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server with module usage data"""
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
                    "calls": [{"module": "User", "function": "create", "arity": 1, "line": 10}],
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
    async def test_module_not_found(self, test_server):
        """Should return error when module doesn't exist"""
        result = await test_server._search_module_usage("NonExistent.Module", "markdown")
        assert len(result) == 1
        assert "not found in index" in result[0].text

    @pytest.mark.asyncio
    async def test_finds_usage_patterns(self, test_server):
        """Should find aliases, imports, and function calls"""
        result = await test_server._search_module_usage("MyApp.User", "markdown")
        assert len(result) == 1
        text = result[0].text
        assert "MyApp.Account" in text
        assert "alias" in text.lower() or "Aliases" in text
        assert "import" in text.lower() or "Imports" in text
        assert "create/1" in text


class TestListTools:
    """Test list_tools functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance"""
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
    async def test_returns_all_expected_tools(self, test_server):
        """Should return all expected tools"""
        tools = await test_server.list_tools()
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "search_module",
            "search_function",
            "search_module_usage",
            "find_pr_for_line",
            "get_commit_history",
            "get_blame",
            "get_file_pr_history",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found"

    @pytest.mark.asyncio
    async def test_tools_have_descriptions_and_schemas(self, test_server):
        """Should have descriptions and input schemas for all tools"""
        tools = await test_server.list_tools()

        for tool in tools:
            assert tool.description, f"Tool '{tool.name}' missing description"
            assert len(tool.description) > 10, f"Tool '{tool.name}' has short description"
            assert tool.inputSchema, f"Tool '{tool.name}' missing inputSchema"
            assert "properties" in tool.inputSchema, f"Tool '{tool.name}' schema missing properties"


class TestUnknownTool:
    """Test handling of unknown tool names."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance"""
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
    async def test_raises_error(self, test_server):
        """Should raise ValueError for unknown tools"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await test_server.call_tool("nonexistent_tool", {})


class TestAddCodeExamples:
    """Test _add_code_examples functionality."""

    @pytest.fixture
    def test_server_with_files(self, tmp_path):
        """Create a test server with actual code files"""
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

    def test_adds_code_to_call_sites(self, test_server_with_files):
        """Should add code examples to call sites"""
        call_sites = [
            {
                "file": "lib/test.ex",
                "line": 3,
                "calling_module": "Test",
                "calling_function": {"name": "function1", "arity": 0},
            }
        ]

        test_server_with_files._add_code_examples(call_sites)

        assert "code_line" in call_sites[0]
        assert "call_target()" in str(call_sites[0]["code_line"])

    def test_handles_missing_files_gracefully(self, test_server_with_files):
        """Should skip code examples for missing files"""
        call_sites = [{"file": "lib/nonexistent.ex", "line": 10, "calling_module": "Test"}]

        test_server_with_files._add_code_examples(call_sites)

        assert "code_line" not in call_sites[0]


class TestParseChangedSince:
    """Test _parse_changed_since date parsing logic."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance"""
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

    def test_parse_iso_date(self, test_server):
        """Should parse ISO date format and ensure timezone-aware"""
        from datetime import datetime, timezone

        result = test_server._parse_changed_since("2024-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        # Should be timezone-aware (UTC assumed for naive dates)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_parse_relative_days(self, test_server):
        """Should parse relative days format and ensure timezone-aware"""
        from datetime import datetime, timedelta, timezone

        result = test_server._parse_changed_since("7d")
        expected = datetime.now(timezone.utc) - timedelta(days=7)
        assert isinstance(result, datetime)
        # Should be timezone-aware
        assert result.tzinfo is not None
        # Allow 1-second tolerance for execution time
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_weeks(self, test_server):
        """Should parse relative weeks format and ensure timezone-aware"""
        from datetime import datetime, timedelta, timezone

        result = test_server._parse_changed_since("2w")
        expected = datetime.now(timezone.utc) - timedelta(weeks=2)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_months(self, test_server):
        """Should parse relative months format and ensure timezone-aware"""
        from datetime import datetime, timedelta, timezone

        result = test_server._parse_changed_since("3m")
        expected = datetime.now(timezone.utc) - timedelta(days=3 * 30)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_years(self, test_server):
        """Should parse relative years format and ensure timezone-aware"""
        from datetime import datetime, timedelta, timezone

        result = test_server._parse_changed_since("1y")
        expected = datetime.now(timezone.utc) - timedelta(days=365)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_invalid_format_raises_error(self, test_server):
        """Should raise ValueError for invalid format"""
        with pytest.raises(ValueError, match="Invalid changed_since format"):
            test_server._parse_changed_since("invalid")

    def test_parse_iso_datetime(self, test_server):
        """Should parse full ISO datetime with time and ensure timezone-aware"""
        from datetime import datetime, timezone

        result = test_server._parse_changed_since("2024-03-20T14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20
        assert result.hour == 14
        assert result.minute == 30
        # Should be timezone-aware (UTC assumed for naive dates)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_parse_iso_datetime_with_timezone(self, test_server):
        """Should preserve timezone info when provided"""
        from datetime import datetime, timezone, timedelta

        # Test with explicit timezone
        result = test_server._parse_changed_since("2024-03-20T14:30:00+05:00")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        # Should preserve the provided timezone (UTC+5)
        assert result.tzinfo == timezone(timedelta(hours=5))

    def test_timezone_aware_comparison_compatibility(self, test_server):
        """Ensure returned datetimes can be compared without TypeError"""
        from datetime import datetime, timezone

        # All these should return timezone-aware datetimes that can be compared
        dt1 = test_server._parse_changed_since("2024-01-15")
        dt2 = test_server._parse_changed_since("7d")
        dt3 = test_server._parse_changed_since("2024-03-20T14:30:00")

        # These comparisons should not raise TypeError
        assert dt1 < dt3  # ISO date vs ISO datetime
        assert dt2 > dt1  # Relative vs ISO date
        assert dt1 < datetime.now(timezone.utc)  # Can compare with timezone-aware now

    def test_negative_value_raises_error(self, test_server):
        """Should reject negative time values"""
        with pytest.raises(ValueError, match="Time amount must be positive"):
            test_server._parse_changed_since("-5d")

    def test_zero_value_raises_error(self, test_server):
        """Should reject zero time values"""
        with pytest.raises(ValueError, match="Time amount must be positive"):
            test_server._parse_changed_since("0d")

    def test_negative_weeks_raises_error(self, test_server):
        """Should reject negative weeks"""
        with pytest.raises(ValueError, match="Time amount must be positive"):
            test_server._parse_changed_since("-2w")

    def test_zero_months_raises_error(self, test_server):
        """Should reject zero months"""
        with pytest.raises(ValueError, match="Time amount must be positive"):
            test_server._parse_changed_since("0m")

    def test_malformed_relative_format(self, test_server):
        """Should reject malformed relative formats"""
        with pytest.raises(ValueError, match="Invalid changed_since format"):
            test_server._parse_changed_since("abc")

    def test_empty_amount(self, test_server):
        """Should reject relative format without amount"""
        with pytest.raises(ValueError):
            test_server._parse_changed_since("d")

    def test_invalid_unit(self, test_server):
        """Should reject invalid time units"""
        with pytest.raises(ValueError, match="Invalid changed_since format"):
            test_server._parse_changed_since("5x")  # 'x' is not a valid unit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
