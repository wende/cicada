"""
Tests for extended git history features: precise tracking, evolution, and blame.
"""

from pathlib import Path

import pytest

from cicada.git_helper import GitHelper


@pytest.fixture
def git_helper():
    """Fixture to create a GitHelper instance for the current repo."""
    repo_path = Path.cwd()
    return GitHelper(str(repo_path))


class TestPreciseFunctionHistory:
    """Tests for git log -L based precise function tracking."""

    def test_function_tracking_basic(self, git_helper):
        """Test function-based tracking using git log -L :funcname:file."""
        # Use a function we know exists in the repo
        file_path = "cicada/git_helper.py"
        function_name = "get_pr_info"

        commits = git_helper.get_function_history_precise(
            file_path, function_name=function_name, max_commits=5
        )

        # Should return some commits (might be 0 if function hasn't changed)
        assert isinstance(commits, list)
        # If commits found, check structure
        if commits:
            commit = commits[0]
            assert "sha" in commit
            assert "full_sha" in commit
            assert "author" in commit
            assert "author_email" in commit
            assert "date" in commit
            assert "summary" in commit

    def test_function_tracking_with_fallback(self, git_helper):
        """Test function tracking with fallback to line tracking."""
        file_path = "cicada/git_helper.py"
        function_name = "nonexistent_function"
        start_line = 15
        end_line = 30

        # Should try function tracking, fail, then fallback to line tracking
        commits = git_helper.get_function_history_precise(
            file_path,
            start_line=start_line,
            end_line=end_line,
            function_name=function_name,
            max_commits=5,
        )

        # Should return commits from fallback
        assert isinstance(commits, list)

    def test_line_tracking_basic(self, git_helper):
        """Test line-based tracking using git log -L start,end:file."""
        # Use a file and line range we know exists in the repo
        file_path = "cicada/git_helper.py"

        # Get the GitHelper class definition (approximate lines)
        # In the actual file, class GitHelper starts around line 15
        start_line = 15
        end_line = 30

        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=5
        )

        # Should return some commits (might be 0 if lines haven't changed)
        assert isinstance(commits, list)
        # If commits found, check structure
        if commits:
            commit = commits[0]
            assert "sha" in commit
            assert "full_sha" in commit
            assert "author" in commit
            assert "author_email" in commit
            assert "date" in commit
            assert "summary" in commit

    def test_precise_history_no_changes(self, git_helper):
        """Test precise history for lines that may not have changed much."""
        file_path = "cicada/git_helper.py"

        # Use a very small range - may have no commits if never changed
        start_line = 1
        end_line = 5

        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=10
        )

        # Should return a list (possibly empty)
        assert isinstance(commits, list)

    def test_precise_history_invalid_lines(self, git_helper):
        """Test precise history with invalid line range."""
        file_path = "cicada/git_helper.py"

        # Use line range that exceeds file length
        start_line = 1
        end_line = 999999

        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=5
        )

        # Should handle gracefully and return empty list
        assert isinstance(commits, list)

    def test_precise_history_max_commits(self, git_helper):
        """Test that max_commits parameter is respected."""
        file_path = "README.md"

        # Use full file range
        start_line = 1
        end_line = 50

        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=2
        )

        # Should return at most 2 commits
        assert isinstance(commits, list)
        assert len(commits) <= 2


class TestFunctionEvolution:
    """Tests for function evolution metadata tracking."""

    def test_evolution_with_function_name(self, git_helper):
        """Test evolution metadata using function name."""
        file_path = "cicada/git_helper.py"
        function_name = "get_pr_info"

        evolution = git_helper.get_function_evolution(file_path, function_name=function_name)

        # May be None if no history found
        if evolution:
            assert "created_at" in evolution
            assert "last_modified" in evolution
            assert "total_modifications" in evolution

            # Check structure of created_at
            created = evolution["created_at"]
            assert "sha" in created
            assert "date" in created
            assert "author" in created
            assert "message" in created

            # Check structure of last_modified
            modified = evolution["last_modified"]
            assert "sha" in modified
            assert "date" in modified
            assert "author" in modified
            assert "message" in modified

            # Total modifications should be positive
            assert evolution["total_modifications"] > 0

    def test_evolution_with_line_numbers(self, git_helper):
        """Test evolution metadata using line numbers."""
        file_path = "cicada/git_helper.py"

        # Get evolution for GitHelper class
        start_line = 15
        end_line = 30

        evolution = git_helper.get_function_evolution(
            file_path, start_line=start_line, end_line=end_line
        )

        # May be None if no history found
        if evolution:
            assert "created_at" in evolution
            assert "last_modified" in evolution
            assert "total_modifications" in evolution

    def test_evolution_modification_frequency(self, git_helper):
        """Test modification frequency calculation."""
        file_path = "README.md"

        # README likely has multiple modifications
        start_line = 1
        end_line = 10

        evolution = git_helper.get_function_evolution(
            file_path, start_line=start_line, end_line=end_line
        )

        if evolution and evolution.get("modification_frequency"):
            freq = evolution["modification_frequency"]
            assert isinstance(freq, (int, float))
            assert freq >= 0

    def test_evolution_no_history(self, git_helper):
        """Test evolution for code with no history."""
        file_path = "cicada/git_helper.py"

        # Use lines that may not have history
        start_line = 999999
        end_line = 999999

        evolution = git_helper.get_function_evolution(
            file_path, start_line=start_line, end_line=end_line
        )

        # Should return None for invalid range
        assert evolution is None or isinstance(evolution, dict)


class TestFunctionBlame:
    """Tests for git blame integration."""

    def test_blame_basic(self, git_helper):
        """Test basic git blame functionality."""
        file_path = "cicada/git_helper.py"

        # Get blame for a small section
        start_line = 15
        end_line = 25

        blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

        # Should return a list
        assert isinstance(blame_groups, list)

        # If blame groups found, check structure
        if blame_groups:
            group = blame_groups[0]
            assert "author" in group
            assert "author_email" in group
            assert "sha" in group
            assert "date" in group
            assert "line_start" in group
            assert "line_end" in group
            assert "line_count" in group
            assert "lines" in group

            # Check lines structure
            if group["lines"]:
                line = group["lines"][0]
                assert "number" in line
                assert "content" in line

    def test_blame_grouping(self, git_helper):
        """Test that consecutive lines by same author are grouped."""
        file_path = "cicada/git_helper.py"

        # Get blame for a larger section
        start_line = 15
        end_line = 40

        blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

        # Check that grouping is working
        if blame_groups:
            for group in blame_groups:
                # Each group should have consecutive lines
                assert group["line_count"] == len(group["lines"])

                # Verify lines are consecutive
                if len(group["lines"]) > 1:
                    for i in range(len(group["lines"]) - 1):
                        current_line = group["lines"][i]["number"]
                        next_line = group["lines"][i + 1]["number"]
                        # Lines should be consecutive (may have gaps due to filtering)
                        assert next_line > current_line

    def test_blame_invalid_range(self, git_helper):
        """Test blame with invalid line range."""
        file_path = "cicada/git_helper.py"

        # Invalid range
        start_line = 999999
        end_line = 999999

        blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

        # Should handle gracefully
        assert isinstance(blame_groups, list)

    def test_blame_single_line(self, git_helper):
        """Test blame for a single line."""
        file_path = "cicada/git_helper.py"

        # Single line
        start_line = 15
        end_line = 15

        blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

        # Should return list
        assert isinstance(blame_groups, list)

        if blame_groups:
            # Should have exactly one line
            group = blame_groups[0]
            assert group["line_count"] == 1
            assert len(group["lines"]) == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_nonexistent_file(self, git_helper):
        """Test handling of non-existent files."""
        file_path = "nonexistent_file.txt"

        commits = git_helper.get_function_history_precise(
            file_path, start_line=1, end_line=10, max_commits=5
        )

        # Should handle gracefully (return empty list)
        assert isinstance(commits, list)
        assert len(commits) == 0

    def test_empty_file_range(self, git_helper):
        """Test with start_line > end_line."""
        file_path = "README.md"

        # Reversed range
        start_line = 10
        end_line = 5

        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=5
        )

        # Should handle gracefully
        assert isinstance(commits, list)

    def test_integration_precise_and_evolution(self, git_helper):
        """Test using both precise tracking and evolution together."""
        file_path = "cicada/git_helper.py"

        start_line = 15
        end_line = 30

        # Get both history and evolution
        commits = git_helper.get_function_history_precise(
            file_path, start_line=start_line, end_line=end_line, max_commits=5
        )
        evolution = git_helper.get_function_evolution(
            file_path, start_line=start_line, end_line=end_line
        )

        # Both should work independently
        assert isinstance(commits, list)
        if evolution:
            assert isinstance(evolution, dict)

            # If both have data, they should be consistent
            if commits and evolution:
                # Most recent commit in history should match last_modified
                if len(commits) > 0:
                    assert commits[0]["sha"] == evolution["last_modified"]["sha"]


if __name__ == "__main__":
    print("Running extended git history tests...")
    print("\nNote: Some tests may have empty results if the code hasn't changed.")
    print("This is expected behavior for precise line tracking.\n")

    pytest.main([__file__, "-v"])
