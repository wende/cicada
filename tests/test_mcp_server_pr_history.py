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


class TestFindPRForLine:
    """Test _find_pr_for_line functionality."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with PR index"""
        from cicada.utils import get_pr_index_path

        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {
            "prs": {"123": {"number": 123, "title": "Add feature", "author": "developer"}},
            "commit_to_pr": {"abc123": 123},
        }
        # Use centralized storage for PR index
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
    async def test_no_pr_index(self, tmp_path):
        """Should return error message when PR index doesn't exist"""
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
        assert "cicada index-pr" in result[0].text

    @pytest.mark.asyncio
    async def test_finds_pr_with_mock(self, test_server_with_pr_index):
        """Should find PR using mocked PRFinder"""
        with patch("cicada.mcp.server.PRFinder") as mock_finder_class:
            mock_finder = Mock()
            mock_finder.find_pr_for_line.return_value = {
                "pr": {"number": 123, "title": "Test PR"},
                "commit": {"sha": "abc123"},
            }
            mock_finder.format_result.return_value = "PR #123: Test PR"
            mock_finder_class.return_value = mock_finder

            result = await test_server_with_pr_index._find_pr_for_line("test.ex", 42, "text")

            assert len(result) == 1
            assert "PR #123" in result[0].text


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
        server.git_helper = None

        result = await server._get_function_history("test.ex", 1, 10)

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
        server.git_helper = Mock()
        server.git_helper.get_function_history.return_value = []

        result = await server._get_function_history("test.ex", 1, 10)

        assert len(result) == 1
        assert "No blame information found" in result[0].text


class TestGetFilePRHistory:
    """Test _get_file_pr_history functionality."""

    @pytest.fixture
    def test_server_with_pr_data(self, tmp_path):
        """Create a test server with PR history data"""
        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

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
    async def test_no_pr_index(self, tmp_path):
        """Should return error when PR index is not available"""
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
        assert "cicada index-pr" in result[0].text

    @pytest.mark.asyncio
    async def test_file_not_found(self, test_server_with_pr_data):
        """Should return message when file has no PRs"""
        result = await test_server_with_pr_data._get_file_pr_history("lib/nonexistent.ex")

        assert len(result) == 1
        assert "No pull requests found" in result[0].text

    @pytest.mark.asyncio
    async def test_successful_retrieval(self, test_server_with_pr_data):
        """Should retrieve and format PR history"""
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
        result = test_server._extract_complete_call(lines, line_num)

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

        result = test_server._extract_complete_call(lines, 3)

        assert result is not None
        assert not result.startswith("    ")
        assert "indented_call()" in result

    @pytest.mark.parametrize("line_num", [0, 100])
    def test_invalid_line_numbers(self, line_num, test_server):
        """Should return None for invalid line numbers"""
        lines = ["line1\n", "line2\n"]
        result = test_server._extract_complete_call(lines, line_num)
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
        server.git_helper = Mock()

        return server

    @pytest.mark.asyncio
    async def test_with_evolution_metadata(self, test_server_with_git):
        """Should show evolution metadata when requested"""
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

        assert "Function Evolution" in text
        assert "Created:" in text
        assert "Last Modified:" in text
        assert "5 commit(s)" in text
        assert "Modification Frequency:" in text
        assert "2.5" in text

    @pytest.mark.asyncio
    async def test_no_commits_found(self, test_server_with_git):
        """Should return message when no commits found"""
        test_server_with_git.git_helper.get_file_history.return_value = []

        result = await test_server_with_git._get_file_history("test.ex", max_commits=10)

        assert len(result) == 1
        assert "No commit history found" in result[0].text

    @pytest.mark.asyncio
    async def test_with_full_commit_message(self, test_server_with_git):
        """Should show full commit message when different from summary"""
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

        assert "Full message:" in text
        assert "This is a much longer" in text


class TestFindPRForLineNetworkFallback:
    """Test _find_pr_for_line with network fallback."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with PR index"""
        from cicada.utils import get_pr_index_path

        index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {"prs": {}, "commit_to_pr": {}}
        # Use centralized storage for PR index
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
    async def test_network_fallback_finds_pr(self, test_server_with_pr_index):
        """Should suggest index update when network fallback finds PR"""
        with patch("cicada.mcp.server.PRFinder") as mock_finder_class:
            # Index finder: commit but no PR
            mock_index_finder = Mock()
            mock_index_finder.find_pr_for_line.return_value = {
                "pr": None,
                "commit": {"sha": "abc123"},
            }

            # Network finder: finds the PR
            mock_network_finder = Mock()
            mock_network_finder.find_pr_for_line.return_value = {
                "pr": {"number": 123, "title": "Test PR"},
                "commit": {"sha": "abc123"},
            }

            mock_finder_class.side_effect = [mock_index_finder, mock_network_finder]

            result = await test_server_with_pr_index._find_pr_for_line("test.ex", 42, "text")

            assert len(result) == 1
            assert "incomplete" in result[0].text.lower() or "update" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_no_pr_in_both(self, test_server_with_pr_index):
        """Should not suggest update when commit truly has no PR"""
        with patch("cicada.mcp.server.PRFinder") as mock_finder_class:
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

            result = await test_server_with_pr_index._find_pr_for_line("test.ex", 42, "text")

            assert len(result) == 1
            assert "Commit abc123" in result[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
