"""
Tests for PR Finder module.
"""

import pytest
from pathlib import Path
from cicada.pr_finder import PRFinder


def test_pr_finder_initialization():
    """Test that PR finder initializes correctly."""
    finder = PRFinder()
    assert finder.repo_path.exists()
    assert (finder.repo_path / ".git").exists()


def test_pr_finder_invalid_repo():
    """Test that PR finder raises error for invalid repo."""
    with pytest.raises(ValueError):
        PRFinder(repo_path="/tmp/nonexistent")


def test_find_pr_for_line():
    """Test finding PR for a specific line."""
    finder = PRFinder()

    # Test with README.md line 1 (should have a commit)
    result = finder.find_pr_for_line("README.md", 1)

    assert "file_path" in result
    assert "line_number" in result
    assert "commit" in result
    assert result["file_path"] == "README.md"
    assert result["line_number"] == 1
    assert result["commit"] is not None


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
        }
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
        }
    }

    output = finder.format_result(result, "markdown")
    assert "## Line 10" in output
    assert "abc123" in output
    assert "#42" in output
    assert "Add feature" in output


def test_format_result_no_pr():
    """Test formatting when no PR is found."""
    finder = PRFinder()
    result = {
        "file_path": "test.py",
        "line_number": 10,
        "commit": "abc123",
        "pr": None
    }

    output = finder.format_result(result, "text")
    assert "PR: None" in output
    assert "abc123" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
