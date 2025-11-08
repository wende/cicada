"""
Tests for PR Finder module.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cicada.pr_finder import PRFinder


def test_pr_finder_initialization():
    """Test that PR finder initializes correctly."""
    finder = PRFinder()
    assert finder.repo_path.exists()
    assert (finder.repo_path / ".git").exists()


def test_pr_finder_invalid_repo():
    """Test that PR finder raises error for invalid repo."""
    with pytest.raises(ValueError):
        _ = PRFinder(repo_path="/tmp/nonexistent")


@patch("subprocess.run")
def test_find_pr_for_line(mock_run):
    """Test finding PR for a specific line."""

    # Mock git blame to return commit info
    def run_side_effect(cmd, **kwargs):
        if "blame" in cmd:
            return Mock(
                stdout="abc123\tJohn Doe\tjohn@example.com\t2024-01-01 00:00:00 +0000",
                returncode=0,
            )
        elif "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            # Return empty PR list to avoid network lookup
            return Mock(stdout="[]", returncode=0)
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    result = finder.find_pr_for_line("README.md", 1)

    assert "file_path" in result
    assert "line_number" in result
    assert "commit" in result
    assert result["file_path"] == "README.md"
    assert result["line_number"] == 1
    assert result["commit"] == "abc123"


def test_format_result_json():
    """Test JSON formatting."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "pr": {
            "number": 42,
            "title": "Add feature",
            "url": "https://github.com/user/repo/pull/42",
            "state": "closed",
            "merged": True,
            "author": "testuser",
            "created_at": "2024-01-01T00:00:00Z",
            "merged_at": "2024-01-02T00:00:00Z",
        },
    }

    output = finder.format_result(result, "json")
    assert "abc123" in output
    assert "42" in output


def test_format_result_markdown():
    """Test Markdown formatting."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "pr": {
            "number": 42,
            "title": "Add feature",
            "url": "https://github.com/user/repo/pull/42",
            "state": "closed",
            "merged": True,
            "author": "testuser",
            "created_at": "2024-01-01T00:00:00Z",
            "merged_at": "2024-01-02T00:00:00Z",
        },
    }

    output = finder.format_result(result, "markdown")
    assert "## Line 10" in output
    assert "abc123" in output
    assert "#42" in output
    assert "Add feature" in output


def test_format_result_no_pr():
    """Test formatting when no PR is found."""
    finder = PRFinder()
    result = {"file_path": "test.py", "line_number": 10, "commit": "abc123", "pr": None}

    output = finder.format_result(result, "text")
    assert "PR: None" in output
    assert "abc123" in output


def test_pr_finder_with_index():
    """Test PR finder with index enabled."""
    finder = PRFinder(use_index=True, index_path=".cicada/pr_index.json")
    assert finder.use_index is True


def test_pr_finder_without_index():
    """Test PR finder with index disabled."""
    # Mock gh CLI validation to avoid requiring gh CLI
    with patch("cicada.pr_finder.subprocess.run"):
        finder = PRFinder(use_index=False)
        assert finder.use_index is False


def test_lookup_pr_in_index_no_index():
    """Test PR lookup when index is None."""
    finder = PRFinder()
    finder.index = None
    result = finder._lookup_pr_in_index("abc123")
    assert result is None


def test_lookup_pr_in_index_commit_not_found():
    """Test PR lookup when commit is not in index."""
    finder = PRFinder()
    finder.index = {
        "commit_to_pr": {"def456": 123},
        "prs": {"123": {"number": 123, "title": "Test"}},
    }
    result = finder._lookup_pr_in_index("abc123")
    assert result is None


def test_lookup_pr_in_index_pr_not_found():
    """Test PR lookup when PR number exists but PR details missing."""
    finder = PRFinder()
    finder.index = {
        "commit_to_pr": {"abc123": 999},
        "prs": {"123": {"number": 123, "title": "Test"}},
    }
    result = finder._lookup_pr_in_index("abc123")
    assert result is None


def test_lookup_pr_in_index_success():
    """Test successful PR lookup from index."""
    finder = PRFinder()
    pr_data = {"number": 42, "title": "Fix bug", "state": "closed"}
    finder.index = {
        "commit_to_pr": {"abc123": 42},
        "prs": {"42": pr_data},
    }
    result = finder._lookup_pr_in_index("abc123")
    assert result == pr_data


def test_run_git_blame_error():
    """Test git blame error handling."""
    with patch("cicada.pr_finder.PRFinder") as mock_finder_class:
        # Create a real finder instance
        finder = PRFinder()

        # Mock subprocess to raise an error
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("git blame failed")

            with pytest.raises(Exception):
                finder._run_git_blame("test.py", 10)


@patch("subprocess.run")
def test_get_repo_info_success(mock_run):
    """Test successful repository info retrieval."""
    mock_run.return_value = Mock(stdout="owner/repo\n", stderr="", returncode=0)

    finder = PRFinder()
    result = finder._get_repo_info()

    assert result == ("owner", "repo")


@patch("subprocess.run")
def test_get_repo_info_null_output(mock_run):
    """Test repository info when output is null."""
    mock_run.return_value = Mock(stdout="null\n", stderr="", returncode=0)

    finder = PRFinder()
    result = finder._get_repo_info()

    assert result is None


@patch("subprocess.run")
def test_get_repo_info_empty_output(mock_run):
    """Test repository info when output is empty."""
    mock_run.return_value = Mock(stdout="\n", stderr="", returncode=0)

    finder = PRFinder()
    result = finder._get_repo_info()

    assert result is None


@patch("subprocess.run")
def test_get_repo_info_error(mock_run):
    """Test repository info retrieval error."""
    from subprocess import CalledProcessError

    def run_side_effect(cmd, **kwargs):
        # Allow gh --version to succeed (for validation)
        if "--version" in cmd:
            return Mock(stdout="gh version 2.0.0\n", returncode=0)
        # Make gh repo view fail
        raise CalledProcessError(1, "gh repo view", stderr="error")

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    result = finder._get_repo_info()

    assert result is None


def test_format_result_error():
    """Test formatting result with error."""
    finder = PRFinder()
    result = {"error": "Could not find commit for this line"}

    output = finder.format_result(result, "text")
    assert "Error: Could not find commit for this line" in output


def test_format_result_text_with_full_author_info():
    """Test text formatting with full author information."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abcdef1234567890",
        "author_name": "John Doe",
        "author_email": "john@example.com",
        "pr": None,
    }

    output = finder.format_result(result, "text")
    assert "File: test.py:10" in output
    assert "Commit: abcdef1" in output  # Short SHA
    assert "Author: John Doe <john@example.com>" in output


def test_format_result_text_with_name_only():
    """Test text formatting with only author name."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": "John Doe",
        "author_email": None,
        "pr": None,
    }

    output = finder.format_result(result, "text")
    assert "Author: John Doe" in output


def test_format_result_text_with_email_only():
    """Test text formatting with only author email."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": None,
        "author_email": "john@example.com",
        "pr": None,
    }

    output = finder.format_result(result, "text")
    assert "Author: john@example.com" in output


def test_format_result_text_with_unknown_author():
    """Test text formatting with no author information."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": None,
        "author_email": None,
        "pr": None,
    }

    output = finder.format_result(result, "text")
    assert "Author: Unknown" in output


def test_format_result_markdown_with_author_info():
    """Test markdown formatting with author information."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abcdef1234567890",
        "author_name": "John Doe",
        "author_email": "john@example.com",
        "pr": None,
    }

    output = finder.format_result(result, "markdown")
    assert "## Line 10 in test.py" in output
    assert "**Commit:** `abcdef1`" in output
    assert "**Author:** John Doe <john@example.com>" in output


def test_format_result_markdown_with_pr_state():
    """Test markdown formatting with PR state."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": "John",
        "author_email": None,
        "pr": {
            "number": 42,
            "title": "Add feature",
            "url": "https://github.com/user/repo/pull/42",
            "state": "open",
            "merged": False,
            "author": "testuser",
        },
    }

    output = finder.format_result(result, "markdown")
    assert "**PR:** [#42]" in output
    assert "open" in output


def test_format_result_text_with_note():
    """Test text formatting with note field."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": "John",
        "author_email": None,
        "pr": None,
        "note": "Direct commit to main",
    }

    output = finder.format_result(result, "text")
    assert "PR: Direct commit to main" in output


def test_format_result_markdown_with_note():
    """Test markdown formatting with note field."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "author_name": "John",
        "author_email": None,
        "pr": None,
        "note": "Direct commit",
    }

    output = finder.format_result(result, "markdown")
    assert "**PR:** Direct commit" in output


def test_format_result_short_commit():
    """Test that short commits (< 7 chars) are not truncated."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc",
        "author_name": "John",
        "author_email": None,
        "pr": None,
    }

    output = finder.format_result(result, "text")
    assert "Commit: abc" in output


@patch("subprocess.run")
def test_find_pr_for_line_absolute_path(mock_run):
    """Test find_pr_for_line with absolute path."""

    # Mock git blame to return commit info
    def run_side_effect(cmd, **kwargs):
        if "blame" in cmd:
            return Mock(
                stdout="abc123\tJohn Doe\tjohn@example.com\t2024-01-01 00:00:00 +0000",
                returncode=0,
            )
        elif "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            # Return empty PR list to avoid network lookup
            return Mock(stdout="[]", returncode=0)
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    abs_path = finder.repo_path / "README.md"

    result = finder.find_pr_for_line(str(abs_path), 1)

    assert result["file_path"] == "README.md"
    assert result["line_number"] == 1


def test_validate_git_repo_nonexistent():
    """Test validation fails for nonexistent directory."""
    with pytest.raises(ValueError, match="Not a git repository"):
        PRFinder(repo_path="/tmp/definitely_not_a_git_repo_12345")


@patch("subprocess.run")
def test_validate_gh_cli_not_installed(mock_run):
    """Test validation fails when gh CLI is not installed."""
    mock_run.side_effect = FileNotFoundError()

    with pytest.raises(RuntimeError, match="GitHub CLI.*not installed"):
        # Force validation by disabling index
        PRFinder(use_index=False)


@patch("subprocess.run")
def test_validate_gh_cli_error(mock_run):
    """Test validation fails when gh CLI returns error."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "gh --version")

    with pytest.raises(RuntimeError, match="GitHub CLI.*not installed"):
        PRFinder(use_index=False)


def test_load_index_not_found():
    """Test loading index when file doesn't exist."""
    finder = PRFinder(use_index=True, index_path=".cicada/nonexistent_pr_index.json")
    # Should load as None and show warning
    assert finder.index is None


@patch("subprocess.run")
def test_find_pr_for_commit_not_github_repo(mock_run):
    """Test finding PR when not a GitHub repository."""
    mock_run.return_value = Mock(stdout="null\n", stderr="", returncode=0)

    finder = PRFinder()
    result = finder._find_pr_for_commit("abc123")

    assert result is None


@patch("subprocess.run")
def test_find_pr_for_commit_no_prs(mock_run):
    """Test finding PR when commit has no associated PRs."""

    def run_side_effect(cmd, **kwargs):
        if "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            return Mock(stdout="[]", returncode=0)
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    result = finder._find_pr_for_commit("abc123")

    assert result is None


@patch("subprocess.run")
def test_find_pr_for_commit_api_error(mock_run):
    """Test finding PR when API call fails."""
    from subprocess import CalledProcessError

    def run_side_effect(cmd, **kwargs):
        if "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            raise CalledProcessError(1, "gh api")
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    result = finder._find_pr_for_commit("abc123")

    assert result is None


@patch("subprocess.run")
def test_find_pr_for_commit_invalid_json(mock_run):
    """Test finding PR when API returns invalid JSON."""

    def run_side_effect(cmd, **kwargs):
        if "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            return Mock(stdout="invalid json", returncode=0)
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()

    with pytest.raises(RuntimeError, match="Failed to parse PR information"):
        finder._find_pr_for_commit("abc123")


@patch("subprocess.run")
def test_find_pr_for_commit_success(mock_run):
    """Test successful PR finding from commit."""
    pr_data = {
        "number": 42,
        "title": "Fix bug",
        "html_url": "https://github.com/owner/repo/pull/42",
        "state": "closed",
        "merged_at": "2024-01-01T00:00:00Z",
        "user": {"login": "testuser"},
        "created_at": "2024-01-01T00:00:00Z",
    }

    def run_side_effect(cmd, **kwargs):
        if "repo" in cmd and "view" in cmd:
            return Mock(stdout="owner/repo\n", returncode=0)
        elif "api" in cmd:
            return Mock(stdout=json.dumps([pr_data]), returncode=0)
        return Mock(stdout="", returncode=0)

    mock_run.side_effect = run_side_effect

    finder = PRFinder()
    result = finder._find_pr_for_commit("abc123")

    assert result is not None
    assert result["number"] == 42
    assert result["title"] == "Fix bug"
    assert result["merged"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
