"""Tests for Git formatter."""

import pytest

from cicada.git.formatter import GitFormatter


class TestGitFormatterFormatResult:
    """Tests for format_result method."""

    def test_format_result_with_error(self):
        """Test formatting when data is None."""
        result = {"type": "file", "data": None, "error": "File not found"}
        output = GitFormatter.format_result(result)
        assert "**Error:** File not found" in output

    def test_format_result_unknown_type(self):
        """Test formatting with unknown result type."""
        result = {"type": "unknown", "data": {"some": "data"}}
        output = GitFormatter.format_result(result)
        assert "**Unknown result type:** unknown" in output

    def test_format_result_file_type_without_pr(self):
        """Test formatting file result without PR enrichment."""
        result = {
            "type": "file",
            "data": {
                "file_path": "lib/example.ex",
                "commits": [
                    {
                        "sha": "abc123",
                        "date": "2024-01-15T10:00:00",
                        "author": "developer",
                        "summary": "Add feature",
                    }
                ],
            },
            "pr_enriched": False,
        }
        output = GitFormatter.format_result(result)
        assert "## History for lib/example.ex" in output
        assert "abc123" in output
        assert "@developer" in output
        assert "Add feature" in output

    def test_format_result_file_type_with_pr(self):
        """Test formatting file result with PR enrichment."""
        result = {
            "type": "file",
            "data": {
                "file_path": "lib/example.ex",
                "prs": [
                    {
                        "number": 42,
                        "title": "Feature PR",
                        "author": "developer",
                        "merged_at": "2024-01-15T10:00:00",
                    }
                ],
            },
            "pr_enriched": True,
        }
        output = GitFormatter.format_result(result)
        assert "## History for lib/example.ex" in output
        assert "PR #42" in output
        assert '"Feature PR"' in output
        assert "@developer" in output


class TestFormatFileMethod:
    """Tests for _format_file method."""

    def test_format_file_no_commits_with_filter(self):
        """Test formatting when no commits match filter."""
        data = {
            "file_path": "lib/example.ex",
            "commits": [],
            "filter_desc": "last 14 days",
        }
        output = GitFormatter._format_file(data, pr_enriched=False)
        assert "No commits matching: last 14 days" in output

    def test_format_file_compact_commits(self):
        """Test compact commit formatting."""
        data = {
            "file_path": "lib/example.ex",
            "commits": [
                {
                    "sha": "abc123",
                    "date": "2024-01-15T10:00:00",
                    "author": "developer",
                    "summary": "Fix bug",
                },
                {
                    "sha": "def456",
                    "date": "2024-01-14T09:00:00",
                    "author": "contributor",
                    "summary": "Add tests",
                },
            ],
        }
        output = GitFormatter._format_file(data, pr_enriched=False)
        assert "- abc123 (2024-01-15) @developer: Fix bug" in output
        assert "- def456 (2024-01-14) @contributor: Add tests" in output

    def test_format_file_no_prs(self):
        """Test formatting when no PRs found."""
        data = {"file_path": "lib/example.ex", "prs": []}
        output = GitFormatter._format_file(data, pr_enriched=True)
        assert "No PRs found for this file" in output

    def test_format_file_compact_pr(self):
        """Test compact PR formatting."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 123,
                    "title": "Big feature",
                    "author": "dev",
                    "merged_at": "2024-03-20T15:00:00",
                }
            ],
        }
        output = GitFormatter._format_file(data, pr_enriched=True)
        assert '- PR #123 "Big feature" @dev 2024-03-20' in output

    def test_format_file_pr_with_created_at_fallback(self):
        """Test PR formatting uses created_at when merged_at is missing."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 456,
                    "title": "Open PR",
                    "author": "dev",
                    "created_at": "2024-02-10T12:00:00",
                }
            ],
        }
        output = GitFormatter._format_file(data, pr_enriched=True)
        assert "@dev 2024-02-10" in output

    def test_format_file_with_include_pr_description(self):
        """Test including PR description."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 100,
                    "title": "Feature",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "description": "This is the PR description.\nWith multiple lines.",
                }
            ],
        }
        opts = {"include_pr_description": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        assert "This is the PR description." in output
        assert "With multiple lines." in output

    def test_format_file_description_truncation(self):
        """Test PR description is truncated when too long."""
        long_description = "\n".join([f"Line {i}" for i in range(20)])
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 100,
                    "title": "Feature",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "description": long_description,
                }
            ],
        }
        opts = {"include_pr_description": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        assert "*(truncated)*" in output
        # First 10 lines should be present
        assert "Line 0" in output
        assert "Line 9" in output
        # Lines after truncation should not be present
        assert "Line 15" not in output

    def test_format_file_with_include_review_comments(self):
        """Test including PR review comments."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 200,
                    "title": "Update",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "comments": [
                        {
                            "line": 42,
                            "author": "reviewer",
                            "body": "Nice change!",
                            "resolved": False,
                        }
                    ],
                }
            ],
        }
        opts = {"include_review_comments": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        assert "**Comments:**" in output
        assert "L42 @reviewer: Nice change!" in output

    def test_format_file_comment_resolved_indicator(self):
        """Test resolved comment shows checkmark."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 300,
                    "title": "Fix",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "comments": [
                        {
                            "line": 10,
                            "author": "reviewer",
                            "body": "Fixed!",
                            "resolved": True,
                        }
                    ],
                }
            ],
        }
        opts = {"include_review_comments": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        # Resolved comment should have checkmark
        assert "\u2713" in output  # checkmark

    def test_format_file_pr_comment_without_line(self):
        """Test PR-level comment (no line number)."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 400,
                    "title": "PR",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "comments": [
                        {
                            "line": None,
                            "author": "reviewer",
                            "body": "LGTM!",
                            "resolved": False,
                        }
                    ],
                }
            ],
        }
        opts = {"include_review_comments": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        assert "PR @reviewer: LGTM!" in output

    def test_format_file_verbose_mode(self):
        """Test verbose mode enables all options."""
        data = {
            "file_path": "lib/example.ex",
            "prs": [
                {
                    "number": 500,
                    "title": "Full PR",
                    "author": "dev",
                    "merged_at": "2024-01-01T00:00:00",
                    "description": "Full description here",
                    "comments": [
                        {
                            "line": 5,
                            "author": "reviewer",
                            "body": "Comment body",
                            "resolved": False,
                        }
                    ],
                }
            ],
        }
        opts = {"include_pr_description": True, "include_review_comments": True}
        output = GitFormatter._format_file(data, pr_enriched=True, opts=opts)
        assert "Full description here" in output
        assert "Comment body" in output
