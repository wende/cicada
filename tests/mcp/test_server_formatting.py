#!/usr/bin/env python
"""
Tests for MCP server output formatting.

Tests output formatting for blame information and PR history.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from cicada.mcp.server import CicadaServer


class TestGetFunctionBlameFormatting:
    """Test get_blame formatting scenarios."""

    @pytest.fixture
    def test_server_with_git(self, tmp_path):
        """Create a test server with mocked git helper"""
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
        # After refactoring, mock the git_helper in git_handler
        server.git_handler.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_with_multiple_authorship_groups(self, test_server_with_git):
        """Should format blame with multiple authorship groups"""
        test_server_with_git.git_handler.git_helper.get_function_history.return_value = [
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

        # After refactoring, call git_handler.get_function_blame
        result = await test_server_with_git.git_handler.get_function_blame("test.ex", 10, 13)

        assert len(result) == 1
        text = result[0].text

        # Check for multiple groups with new format
        assert "## 1/2" in text
        assert "## 2/2" in text
        assert "dev1" in text
        assert "dev2" in text

        # Check line ranges with new format
        assert "Lines 10-12" in text
        assert "Lines 13-13" in text

        # Check code content
        assert "def function do" in text
        assert "z = 3" in text

    @pytest.mark.asyncio
    async def test_error_handling(self, test_server_with_git):
        """Should handle errors gracefully"""
        test_server_with_git.git_handler.git_helper.get_function_history.side_effect = Exception(
            "Git error"
        )

        # After refactoring, call git_handler.get_function_blame
        result = await test_server_with_git.git_handler.get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "Error getting blame information" in result[0].text


class TestFormatPRContext:
    """Test _format_pr_context helper method."""

    def test_format_pr_context_with_pr_info(self):
        """Should format PR context when PR info is available"""
        from cicada.elixir.format import ModuleFormatter

        pr_info = {
            "number": 123,
            "title": "Add new feature",
            "author": "developer",
            "comment_count": 5,
        }

        result = ModuleFormatter._format_pr_context(pr_info, "lib/test.ex")

        assert len(result) > 0
        text = "\n".join(result)
        assert "PR #123" in text
        assert "Add new feature" in text
        assert "@developer" in text
        assert "5 review comment(s)" in text
        assert "get_file_pr_history" in text

    def test_format_pr_context_with_pr_info_no_comments(self):
        """Should format PR context without comments section"""
        from cicada.elixir.format import ModuleFormatter

        pr_info = {
            "number": 456,
            "title": "Bug fix",
            "author": "dev2",
            "comment_count": 0,
        }

        result = ModuleFormatter._format_pr_context(pr_info, "lib/test.ex")

        text = "\n".join(result)
        assert "PR #456" in text
        assert "Bug fix" in text
        assert "@dev2" in text
        assert "review comment" not in text  # No comment section

    def test_format_pr_context_without_pr_info(self):
        """Should return empty list when PR info unavailable"""
        from cicada.elixir.format import ModuleFormatter

        result = ModuleFormatter._format_pr_context(None, "lib/test.ex")

        assert result == []

    def test_format_pr_context_with_function_name(self):
        """Should return empty list when PR info unavailable (even with function name)"""
        from cicada.elixir.format import ModuleFormatter

        result = ModuleFormatter._format_pr_context(None, "lib/user.ex", "create_user")

        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
