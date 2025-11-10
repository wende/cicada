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
        server.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_with_multiple_authorship_groups(self, test_server_with_git):
        """Should format blame with multiple authorship groups"""
        test_server_with_git.git_helper.get_function_history.return_value = [
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

        result = await test_server_with_git._get_function_history("test.ex", 10, 13)

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
    async def test_error_handling(self, test_server_with_git):
        """Should handle errors gracefully"""
        test_server_with_git.git_helper.get_function_history.side_effect = Exception("Git error")

        result = await test_server_with_git._get_function_history("test.ex", 1, 10)

        assert len(result) == 1
        assert "Error getting blame information" in result[0].text


class TestGetFilePRHistoryFormatting:
    """Test _get_file_pr_history with various formatting scenarios."""

    @pytest.fixture
    def test_server_with_long_description(self, tmp_path):
        """Create a test server with PR data including long descriptions"""
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
        # Use centralized storage for PR index
        from cicada.utils import get_pr_index_path

        pr_index_path = get_pr_index_path(tmp_path)
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
    async def test_long_description_trimmed(self, test_server_with_long_description):
        """Should trim long PR descriptions"""
        result = await test_server_with_long_description._get_file_pr_history("lib/test.ex")

        assert len(result) == 1
        text = result[0].text

        assert "trimmed" in text.lower()
        assert "more lines" in text.lower()

    @pytest.mark.asyncio
    async def test_comment_variations(self, test_server_with_long_description):
        """Should handle different comment formats"""
        result = await test_server_with_long_description._get_file_pr_history("lib/test.ex")

        assert len(result) == 1
        text = result[0].text

        # Comment with line number
        assert "Line 15" in text
        assert "reviewer2" in text
        assert "✓ Resolved" in text

        # Comment without line number
        assert "Original line 20" in text or "unmapped" in text.lower()
        assert "reviewer1" in text

    @pytest.mark.asyncio
    async def test_absolute_path_outside_repo(self, test_server_with_long_description, tmp_path):
        """Should handle absolute paths outside repository"""
        outside_path = Path("/totally/different/path/file.ex")

        result = await test_server_with_long_description._get_file_pr_history(str(outside_path))

        assert len(result) == 1
        assert "not within repository" in result[0].text


class TestFormatPRContext:
    """Test _format_pr_context helper method."""

    def test_format_pr_context_with_pr_info(self):
        """Should format PR context when PR info is available"""
        from cicada.format import ModuleFormatter

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
        from cicada.format import ModuleFormatter

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
        """Should suggest building PR index when PR info unavailable"""
        from cicada.format import ModuleFormatter

        result = ModuleFormatter._format_pr_context(None, "lib/test.ex")

        text = "\n".join(result)
        assert "Want to know why this code exists?" in text
        assert "cicada index-pr" in text
        assert "get_commit_history" in text
        assert "lib/test.ex" in text

    def test_format_pr_context_with_function_name(self):
        """Should include function name in git history suggestion"""
        from cicada.format import ModuleFormatter

        result = ModuleFormatter._format_pr_context(None, "lib/user.ex", "create_user")

        text = "\n".join(result)
        assert 'function_name="create_user"' in text
        assert "lib/user.ex" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
