#!/usr/bin/env python
"""
Tests for MCP server PR history and git functionality.

Tests PR finding, blame tracking, commit history, and git integration.
"""

import json
from unittest.mock import Mock, patch

import pytest
import yaml

from cicada.mcp.server import CicadaServer


class TestGetFunctionBlame:
    """Test get_blame functionality."""

    @pytest.mark.asyncio
    async def test_no_git_helper(self, tmp_path):
        """Should return error when git helper is not available"""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": "/tmp"},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        server.git_handler.git_helper = None

        # After refactoring, use git_handler.get_function_blame
        result = await server.git_handler.get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "not available" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_no_blame_results(self, tmp_path):
        """Should return message when no blame information found"""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        (tmp_path / ".git").mkdir()
        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        server.git_handler.git_helper = Mock()
        server.git_handler.git_helper.get_function_history.return_value = []

        # After refactoring, use git_handler.get_function_blame
        result = await server.git_handler.get_function_blame("test.ex", 1, 10)

        assert len(result) == 1
        assert "No blame information found" in result[0].text


class TestExtractCompleteCall:
    """Test _extract_complete_call functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance"""
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

    @pytest.mark.parametrize(
        "lines,line_num,should_contain",
        [
            (
                ["defmodule Test do\n", "  def func do\n", "    call()\n", "  end\n"],
                3,
                ["call()"],
            ),
            (["first()\n", "second()\n", "third()\n"], 1, ["first()"]),
            (["first()\n", "second()\n", "last()\n"], 3, ["last()"]),
        ],
    )
    def test_extracts_code_with_context(self, lines, line_num, should_contain, test_server):
        """Should extract code with appropriate context"""
        result = test_server.function_handler._extract_complete_call(lines, line_num)

        assert result is not None
        for expected in should_contain:
            assert expected in result

    def test_dedents_code(self, test_server):
        """Should dedent extracted code"""
        lines = [
            "defmodule Test do\n",
            "  def function do\n",
            "    indented_call()\n",
            "  end\n",
        ]

        result = test_server.function_handler._extract_complete_call(lines, 3)

        assert result is not None
        assert not result.startswith("    ")
        assert "indented_call()" in result

    @pytest.mark.parametrize("line_num", [0, 100])
    def test_invalid_line_numbers(self, line_num, test_server):
        """Should return None for invalid line numbers"""
        lines = ["line1\n", "line2\n"]
        result = test_server.function_handler._extract_complete_call(lines, line_num)
        assert result is None


class TestGetCommitHistoryWithEvolution:
    """Test get_commit_history with evolution metadata."""

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
        # After refactoring, mock git_helper in git_handler
        server.git_handler.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_with_evolution_metadata(self, test_server_with_git):
        """Should show evolution metadata when requested"""
        test_server_with_git.git_handler.git_helper.get_function_history_precise.return_value = [
            {
                "sha": "abc123",
                "summary": "Add feature",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Add feature\n\nDetailed description",
            }
        ]
        test_server_with_git.git_handler.git_helper.get_function_evolution.return_value = {
            "created_at": {"date": "2024-01-01", "author": "dev1", "sha": "abc123"},
            "last_modified": {"date": "2024-01-10", "author": "dev2", "sha": "def456"},
            "total_modifications": 5,
            "modification_frequency": 2.5,
        }

        result = await test_server_with_git.git_handler.get_file_history(
            "test.ex",
            function_name="test_func",
            start_line=1,
            end_line=10,
            show_evolution=True,
            max_commits=10,
        )

        assert len(result) == 1
        text = result[0].text

        assert "Function Evolution" in text
        assert "Created:" in text
        assert "Last Modified:" in text
        assert "5 commit(s)" in text
        assert "Modification Frequency:" in text
        assert "2.5" in text

    @pytest.mark.asyncio
    async def test_no_commits_found(self, test_server_with_git):
        """Should return message when no commits found"""
        test_server_with_git.git_handler.git_helper.get_file_history.return_value = []

        result = await test_server_with_git.git_handler.get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        assert "No commit history found" in result[0].text

    @pytest.mark.asyncio
    async def test_with_compact_format(self, test_server_with_git):
        """Should show commit in compact format (SHA • author • date)"""
        test_server_with_git.git_handler.git_helper.get_file_history.return_value = [
            {
                "sha": "abc123",
                "summary": "Short summary",
                "author": "dev1",
                "author_email": "dev1@example.com",
                "date": "2024-01-01",
                "message": "Short summary\n\nThis is a much longer\nmultiline commit message",
            }
        ]

        result = await test_server_with_git.git_handler.get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        text = result[0].text

        # Verify compact format: summary on first line, SHA • author • date on second line
        assert "Short summary" in text, "Should show commit summary"
        assert (
            "abc123 • dev1 • 2024-01-01" in text
        ), "Should show compact format with SHA, author, date"
