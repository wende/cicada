"""
Tests for HistoryAnalyzer - covers PR enrichment, filtering, and error paths.

These tests focus on code paths not covered by the existing git_history_unified tests,
specifically PR enrichment, date/author filtering, and error handling.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cicada.git.history_analyzer import HistoryAnalyzer


@pytest.fixture
def mock_pr_index():
    """Create a mock PR index with test data."""
    return {
        "prs": {
            "1": {
                "number": 1,
                "title": "Add user authentication",
                "author": "alice",
                "status": "merged",
                "merged": True,
                "url": "https://github.com/test/repo/pull/1",
                "created_at": "2024-01-15T10:00:00Z",
                "merged_at": "2024-01-16T14:00:00Z",
                "description": "Implements basic auth",
                "comments": [
                    {"path": "lib/auth.ex", "body": "LGTM"},
                    {"path": "lib/other.ex", "body": "Not relevant"},
                ],
            },
            "2": {
                "number": 2,
                "title": "Fix login bug",
                "author": "bob",
                "status": "merged",
                "merged": True,
                "url": "https://github.com/test/repo/pull/2",
                "created_at": "2024-02-01T09:00:00Z",
                "merged_at": "2024-02-02T11:00:00Z",
                "description": "Fixes edge case in login",
                "comments": [],
            },
        },
        "commit_to_pr": {
            "abc123def456": 1,
            "def456abc123": 2,
        },
        "file_to_prs": {
            "lib/auth.ex": [1, 2],
            "lib/user.ex": [1],
        },
    }


@pytest.fixture
def analyzer_with_mocks(tmp_path, mock_pr_index):
    """Create HistoryAnalyzer with mocked dependencies."""
    # Create a git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    with patch("cicada.git.history_analyzer.GitHelper") as mock_git:
        with patch("cicada.git.history_analyzer.PRFinder"):
            analyzer = HistoryAnalyzer(
                repo_path=str(tmp_path),
                pr_index=mock_pr_index,
                verbose=False,
            )
            analyzer.git_helper = mock_git.return_value
            yield analyzer


class TestPRFinderInitialization:
    """Test PR finder initialization error paths."""

    def test_init_with_import_error(self, tmp_path):
        """Test PR finder gracefully handles import errors."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("cicada.git.history_analyzer.GitHelper"):
            with patch("cicada.git.history_analyzer.HistoryAnalyzer._init_pr_finder") as mock_init:
                mock_init.return_value = None
                analyzer = HistoryAnalyzer(str(tmp_path), verbose=True)
                assert analyzer.pr_finder is None

    def test_init_pr_finder_oserror(self, tmp_path):
        """Test PR finder handles OSError during initialization."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("cicada.git.history_analyzer.GitHelper"):
            with patch(
                "cicada.git.history_analyzer.PRFinder",
                side_effect=OSError("Permission denied"),
            ):
                analyzer = HistoryAnalyzer(str(tmp_path), verbose=True)
                assert analyzer.pr_finder is None

    def test_init_pr_finder_value_error(self, tmp_path):
        """Test PR finder handles ValueError during initialization."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("cicada.git.history_analyzer.GitHelper"):
            with patch(
                "cicada.git.history_analyzer.PRFinder",
                side_effect=ValueError("Invalid config"),
            ):
                analyzer = HistoryAnalyzer(str(tmp_path), verbose=True)
                assert analyzer.pr_finder is None

    def test_init_pr_finder_unexpected_error(self, tmp_path):
        """Test PR finder handles unexpected errors with verbose traceback."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("cicada.git.history_analyzer.GitHelper"):
            with patch(
                "cicada.git.history_analyzer.PRFinder",
                side_effect=RuntimeError("Unexpected"),
            ):
                analyzer = HistoryAnalyzer(str(tmp_path), verbose=True)
                assert analyzer.pr_finder is None


class TestDateFiltering:
    """Test date and author filtering functionality."""

    def test_filter_by_date_no_filters(self, analyzer_with_mocks):
        """Test that no filters returns True."""
        assert analyzer_with_mocks._filter_by_date("2024-01-15T10:00:00", None, None)

    def test_filter_by_date_since_filter(self, analyzer_with_mocks):
        """Test since date filter."""
        since = datetime(2024, 1, 10, tzinfo=timezone.utc)

        # Date after since - should pass
        assert analyzer_with_mocks._filter_by_date("2024-01-15T10:00:00+00:00", since, None)

        # Date before since - should fail
        assert not analyzer_with_mocks._filter_by_date("2024-01-05T10:00:00+00:00", since, None)

    def test_filter_by_date_until_filter(self, analyzer_with_mocks):
        """Test until date filter."""
        until = datetime(2024, 1, 20, tzinfo=timezone.utc)

        # Date before until - should pass
        assert analyzer_with_mocks._filter_by_date("2024-01-15T10:00:00+00:00", None, until)

        # Date after until - should fail
        assert not analyzer_with_mocks._filter_by_date("2024-01-25T10:00:00+00:00", None, until)

    def test_filter_by_date_parse_error(self, analyzer_with_mocks):
        """Test that invalid date strings return True (no filtering on errors)."""
        since = datetime(2024, 1, 10, tzinfo=timezone.utc)

        # Invalid date format should return True (don't filter on error)
        analyzer_with_mocks.verbose = True
        assert analyzer_with_mocks._filter_by_date("not-a-date", since, None)

    def test_author_matches(self):
        """Test author matching."""
        assert HistoryAnalyzer._author_matches("Alice Smith", "alice")
        assert HistoryAnalyzer._author_matches("alice", "alice")
        assert not HistoryAnalyzer._author_matches("Bob Jones", "alice")
        assert HistoryAnalyzer._author_matches("anyone", None)  # No filter
        assert HistoryAnalyzer._author_matches(None, "alice") is False


class TestSingleLineAnalysis:
    """Test single line analysis with PR enrichment."""

    def test_single_line_with_pr_lookup(self, analyzer_with_mocks):
        """Test single line analysis retrieves PR info."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = [
            {
                "author": "alice",
                "author_email": "alice@example.com",
                "sha": "abc123de",
                "full_sha": "abc123def456",
                "date": "2024-01-15T10:00:00+00:00",
                "lines": ["  def authenticate(user)"],
            }
        ]

        # Set up PR finder mock
        analyzer_with_mocks.pr_finder = MagicMock()
        analyzer_with_mocks.pr_finder.find_pr_for_line.return_value = {
            "pr": {
                "number": 1,
                "title": "Add user authentication",
            }
        }

        result = analyzer_with_mocks._analyze_single_line("lib/auth.ex", 42)

        assert result["type"] == "single_line"
        assert result["pr_enriched"] is True
        assert result["data"]["pr"]["number"] == 1

    def test_single_line_pr_lookup_error(self, analyzer_with_mocks):
        """Test single line handles PR lookup errors gracefully."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = [
            {
                "author": "alice",
                "author_email": "alice@example.com",
                "sha": "abc123de",
                "full_sha": "abc123def456",
                "date": "2024-01-15T10:00:00+00:00",
                "lines": [],
            }
        ]

        # Set up PR finder to raise error
        analyzer_with_mocks.pr_finder = MagicMock()
        analyzer_with_mocks.pr_finder.find_pr_for_line.side_effect = RuntimeError("API error")
        analyzer_with_mocks.verbose = True

        result = analyzer_with_mocks._analyze_single_line("lib/auth.ex", 42)

        assert result["type"] == "single_line"
        assert result["pr_enriched"] is False

    def test_single_line_empty_blame(self, analyzer_with_mocks):
        """Test single line with no blame information."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = []

        result = analyzer_with_mocks._analyze_single_line("lib/auth.ex", 42)

        assert result["type"] == "single_line"
        assert result["data"] is None
        assert "error" in result


class TestLineRangeAnalysis:
    """Test line range analysis with PR enrichment."""

    def test_line_range_with_pr_enrichment(self, analyzer_with_mocks, mock_pr_index):
        """Test line range enriches results with PR data from index."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = [
            {
                "author": "alice",
                "author_email": "alice@example.com",
                "sha": "abc123de",
                "full_sha": "abc123def456",
                "date": "2024-01-15T10:00:00+00:00",
                "lines": ["line 1", "line 2"],
            },
            {
                "author": "bob",
                "author_email": "bob@example.com",
                "sha": "def456ab",
                "full_sha": "def456abc123",
                "date": "2024-02-01T09:00:00+00:00",
                "lines": ["line 3"],
            },
        ]

        # Ensure pr_finder and pr_index are set
        analyzer_with_mocks.pr_finder = MagicMock()
        analyzer_with_mocks.pr_index = mock_pr_index

        result = analyzer_with_mocks._analyze_line_range("lib/auth.ex", 1, 10, 10, None, None, None)

        assert result["type"] == "line_range"
        assert result["pr_enriched"] is True
        assert len(result["data"]["groups"]) == 2
        assert result["data"]["groups"][0].get("pr") is not None

    def test_line_range_with_date_filter(self, analyzer_with_mocks):
        """Test line range filtering by date."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = [
            {
                "author": "alice",
                "sha": "abc123de",
                "full_sha": "abc123def456",
                "date": "2024-01-15T10:00:00+00:00",
                "lines": [],
            },
            {
                "author": "bob",
                "sha": "def456ab",
                "full_sha": "def456abc123",
                "date": "2024-02-15T10:00:00+00:00",
                "lines": [],
            },
        ]

        since = datetime(2024, 2, 1, tzinfo=timezone.utc)

        result = analyzer_with_mocks._analyze_line_range(
            "lib/auth.ex", 1, 10, 10, since, None, None
        )

        # Only bob's commit should pass the filter
        assert len(result["data"]["groups"]) == 1
        assert result["data"]["groups"][0]["author"] == "bob"

    def test_line_range_with_author_filter(self, analyzer_with_mocks):
        """Test line range filtering by author."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = [
            {
                "author": "Alice Smith",
                "sha": "abc123de",
                "full_sha": "abc123def456",
                "date": "2024-01-15T10:00:00+00:00",
                "lines": [],
            },
            {
                "author": "Bob Jones",
                "sha": "def456ab",
                "full_sha": "def456abc123",
                "date": "2024-02-01T09:00:00+00:00",
                "lines": [],
            },
        ]

        result = analyzer_with_mocks._analyze_line_range(
            "lib/auth.ex", 1, 10, 10, None, None, "alice"
        )

        assert len(result["data"]["groups"]) == 1
        assert result["data"]["groups"][0]["author"] == "Alice Smith"

    def test_line_range_empty_blame(self, analyzer_with_mocks):
        """Test line range with no blame information."""
        analyzer_with_mocks.git_helper.get_function_history.return_value = []

        result = analyzer_with_mocks._analyze_line_range("lib/auth.ex", 1, 10, 10, None, None, None)

        assert result["data"] is None
        assert "error" in result


class TestFunctionAnalysis:
    """Test function tracking with evolution."""

    def test_function_with_evolution(self, analyzer_with_mocks):
        """Test function analysis with show_evolution=True."""
        analyzer_with_mocks.git_helper.get_function_history_precise.return_value = [
            {
                "sha": "abc123de",
                "author": "alice",
                "date": "2024-01-15T10:00:00+00:00",
                "message": "Initial implementation",
            }
        ]
        analyzer_with_mocks.git_helper.get_function_evolution.return_value = {
            "created_at": "2024-01-01T00:00:00+00:00",
            "total_modifications": 5,
            "frequency": "weekly",
        }

        result = analyzer_with_mocks._analyze_function(
            "lib/auth.ex",
            "authenticate",
            None,
            None,
            True,  # show_evolution
            10,
            None,
            None,
            None,
        )

        assert result["type"] == "function"
        assert result["data"]["evolution"] is not None
        assert result["data"]["evolution"]["total_modifications"] == 5

    def test_function_with_filters(self, analyzer_with_mocks):
        """Test function analysis with date and author filters."""
        analyzer_with_mocks.git_helper.get_function_history_precise.return_value = [
            {
                "sha": "abc123de",
                "author": "Alice Smith",
                "date": "2024-01-15T10:00:00+00:00",
                "message": "Commit 1",
            },
            {
                "sha": "def456ab",
                "author": "Bob Jones",
                "date": "2024-02-15T10:00:00+00:00",
                "message": "Commit 2",
            },
        ]

        since = datetime(2024, 2, 1, tzinfo=timezone.utc)

        result = analyzer_with_mocks._analyze_function(
            "lib/auth.ex",
            "authenticate",
            None,
            None,
            False,
            10,
            since,
            None,
            "bob",
        )

        # Only bob's commit after Feb 1 should pass
        assert len(result["data"]["commits"]) == 1
        assert result["data"]["commits"][0]["author"] == "Bob Jones"

    def test_function_empty_commits(self, analyzer_with_mocks):
        """Test function analysis with no history."""
        analyzer_with_mocks.git_helper.get_function_history_precise.return_value = []

        result = analyzer_with_mocks._analyze_function(
            "lib/auth.ex",
            "nonexistent_func",
            None,
            None,
            False,
            10,
            None,
            None,
            None,
        )

        assert result["data"] is None
        assert "error" in result


class TestFileAnalysis:
    """Test file-level PR history analysis."""

    def test_file_with_pr_index(self, analyzer_with_mocks, mock_pr_index):
        """Test file analysis uses PR index when available."""
        analyzer_with_mocks.pr_index = mock_pr_index

        result = analyzer_with_mocks._analyze_file("lib/auth.ex", 10, None, None, None, False)

        assert result["type"] == "file"
        assert result["pr_enriched"] is True
        assert len(result["data"]["prs"]) == 2

    def test_file_pr_history_with_date_filter(self, analyzer_with_mocks, mock_pr_index):
        """Test file PR history filtering by date."""
        analyzer_with_mocks.pr_index = mock_pr_index

        since = datetime(2024, 1, 20, tzinfo=timezone.utc)

        result = analyzer_with_mocks._get_file_pr_history("lib/auth.ex", 10, since, None, None)

        # Only PR 2 merged after Jan 20
        assert len(result["prs"]) == 1
        assert result["prs"][0]["number"] == 2

    def test_file_pr_history_with_author_filter(self, analyzer_with_mocks, mock_pr_index):
        """Test file PR history filtering by author."""
        analyzer_with_mocks.pr_index = mock_pr_index

        result = analyzer_with_mocks._get_file_pr_history("lib/auth.ex", 10, None, None, "alice")

        assert len(result["prs"]) == 1
        assert result["prs"][0]["author"] == "alice"

    def test_file_pr_history_includes_comments(self, analyzer_with_mocks, mock_pr_index):
        """Test file PR history includes file-specific comments."""
        analyzer_with_mocks.pr_index = mock_pr_index

        result = analyzer_with_mocks._get_file_pr_history("lib/auth.ex", 10, None, None, None)

        # PR 1 has a comment for lib/auth.ex
        pr1 = next(pr for pr in result["prs"] if pr["number"] == 1)
        assert len(pr1["comments"]) == 1
        assert pr1["comments"][0]["body"] == "LGTM"

    def test_file_pr_history_no_prs(self, analyzer_with_mocks, mock_pr_index):
        """Test file PR history returns None when no PRs found."""
        analyzer_with_mocks.pr_index = mock_pr_index

        result = analyzer_with_mocks._get_file_pr_history(
            "lib/nonexistent.ex", 10, None, None, None
        )

        assert result is None

    def test_file_fallback_to_commits(self, analyzer_with_mocks):
        """Test file analysis falls back to git commits when no PR index."""
        analyzer_with_mocks.pr_index = None
        analyzer_with_mocks.git_helper.get_file_history.return_value = [
            {
                "sha": "abc123de",
                "author": "alice",
                "date": "2024-01-15T10:00:00+00:00",
                "message": "Commit message",
            }
        ]

        result = analyzer_with_mocks._analyze_file("lib/auth.ex", 10, None, None, None, False)

        assert result["type"] == "file"
        assert result["pr_enriched"] is False
        assert "commits" in result["data"]

    def test_file_with_filters_uses_filtered_method(self, analyzer_with_mocks):
        """Test file analysis uses filtered method when filters applied."""
        analyzer_with_mocks.pr_index = None
        analyzer_with_mocks.git_helper.get_file_history_filtered.return_value = []

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)

        result = analyzer_with_mocks._analyze_file("lib/auth.ex", 10, since, None, None, False)

        analyzer_with_mocks.git_helper.get_file_history_filtered.assert_called_once()


class TestAnalyzeRouting:
    """Test the analyze() method routing logic."""

    def test_routes_to_single_line(self, analyzer_with_mocks):
        """Test analyze routes to single line when only start_line provided."""
        with patch.object(analyzer_with_mocks, "_analyze_single_line") as mock:
            mock.return_value = {"type": "single_line"}

            result = analyzer_with_mocks.analyze("lib/auth.ex", start_line=42)

            mock.assert_called_once_with("lib/auth.ex", 42)

    def test_routes_to_line_range(self, analyzer_with_mocks):
        """Test analyze routes to line range when start_line and end_line provided."""
        with patch.object(analyzer_with_mocks, "_analyze_line_range") as mock:
            mock.return_value = {"type": "line_range"}

            result = analyzer_with_mocks.analyze("lib/auth.ex", start_line=1, end_line=10)

            mock.assert_called_once()

    def test_routes_to_function(self, analyzer_with_mocks):
        """Test analyze routes to function when function_name provided."""
        with patch.object(analyzer_with_mocks, "_analyze_function") as mock:
            mock.return_value = {"type": "function"}

            result = analyzer_with_mocks.analyze("lib/auth.ex", function_name="authenticate")

            mock.assert_called_once()

    def test_routes_to_file(self, analyzer_with_mocks):
        """Test analyze routes to file when no specific params provided."""
        with patch.object(analyzer_with_mocks, "_analyze_file") as mock:
            mock.return_value = {"type": "file"}

            result = analyzer_with_mocks.analyze("lib/auth.ex")

            mock.assert_called_once()

    def test_recent_filter_parsing(self, analyzer_with_mocks):
        """Test recent filter is correctly converted to date range."""
        since, until = analyzer_with_mocks._parse_recent_filter(True)

        assert since is not None
        assert until is None

        since, until = analyzer_with_mocks._parse_recent_filter(False)

        assert since is None
        assert until is not None

        since, until = analyzer_with_mocks._parse_recent_filter(None)

        assert since is None
        assert until is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
