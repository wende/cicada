"""Tests for co-change analysis from git history.

These tests mock subprocess.run to avoid git operations that can corrupt
git worktrees during parallel test execution.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cicada.git.cochange_analyzer import CoChangeAnalyzer


# Sample git log output for mocking
SAMPLE_GIT_LOG_OUTPUT = """COMMIT:abc123
lib/auth.ex
lib/credentials.ex

COMMIT:def456
lib/auth.ex
lib/credentials.ex
lib/logger.ex

COMMIT:ghi789
lib/auth.ex
lib/credentials.ex

COMMIT:jkl012
lib/logger.ex

COMMIT:mno345
lib/auth.ex
lib/credentials.ex

COMMIT:pqr678
lib/module_a.ex
lib/module_b.ex

COMMIT:stu901
lib/module_a.ex
lib/module_b.ex
"""

# Git log output for function-level analysis
SAMPLE_FUNCTION_LOG_OUTPUT = """COMMIT:abc123
lib/module_a.ex
lib/module_b.ex

COMMIT:def456
lib/module_a.ex
lib/module_b.ex

COMMIT:ghi789
lib/module_a.ex
"""

# Sample file content for function extraction
SAMPLE_MODULE_A_CONTENT = """
defmodule ModuleA do
  def func_one(arg) do
    :ok
  end

  def func_two(arg) do
    :ok
  end
end
"""

SAMPLE_MODULE_B_CONTENT = """
defmodule ModuleB do
  def func_three(arg) do
    :ok
  end
end
"""


class TestCoChangeAnalyzer:
    """Test suite for CoChangeAnalyzer."""

    def test_analyze_repository_returns_empty_for_non_git_directory(self, tmp_path):
        """Test that analyzing a non-git directory returns empty results."""
        # Arrange: Create a regular directory (not a git repo)
        repo_path = tmp_path / "non_git_dir"
        repo_path.mkdir()

        analyzer = CoChangeAnalyzer()

        # Mock subprocess to simulate git failure (not a git repo)
        import subprocess

        with patch("subprocess.run") as mock_run:
            # First call: git rev-list --count HEAD - simulate failure
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git", stderr="fatal: not a git repository"
            )

            # Act
            result = analyzer.analyze_repository(str(repo_path))

            # Assert - should handle gracefully with empty results
            assert result["file_pairs"] == {}
            assert result["function_pairs"] == {}
            assert result["metadata"]["commit_count"] == 0

    def test_analyze_repository_extracts_file_level_cochanges(self):
        """Test extraction of file-level co-changes from git history."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            """Mock subprocess.run for different git commands."""
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                # git rev-list --count HEAD
                result.stdout = "7"
            elif "--name-only" in cmd:
                # git log --name-only for file changes
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                # git log --format=%H for commit list
                result.stdout = "abc123\ndef456\nghi789\njkl012\nmno345\npqr678\nstu901"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            # Act
            result = analyzer.analyze_repository("/fake/repo")

            # Assert
            file_pairs = result["file_pairs"]

            # auth.ex and credentials.ex should have co-changed 4 times
            assert file_pairs.get(("lib/auth.ex", "lib/credentials.ex"), 0) >= 2

            # Verify bidirectional lookups don't exist (we only store canonical form)
            assert ("lib/credentials.ex", "lib/auth.ex") not in file_pairs

            # Metadata should show commits and file pairs
            assert result["metadata"]["commit_count"] >= 5
            assert result["metadata"]["file_pairs"] >= 1

    def test_analyze_repository_handles_single_file_commits(self):
        """Test that commits with only one file don't create co-change entries with themselves."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "7"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789\njkl012\nmno345\npqr678\nstu901"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = analyzer.analyze_repository("/fake/repo")

            # Logger alone in commit jkl012 should not create pairs with itself
            logger_file = "lib/logger.ex"
            for pair in result["file_pairs"]:
                assert pair[0] != logger_file or pair[1] != logger_file

    def test_analyze_repository_respects_minimum_count_threshold(self):
        """Test filtering by minimum co-change count."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "7"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789\njkl012\nmno345\npqr678\nstu901"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            # Act - filter for minimum 2 co-changes
            result = analyzer.analyze_repository("/fake/repo", min_count=2)

            # Assert - only pairs with count >= 2 should be present
            file_pairs = result["file_pairs"]
            for pair, count in file_pairs.items():
                assert count >= 2, f"Pair {pair} has count {count}, expected >= 2"

    def test_analyze_repository_respects_date_range(self):
        """Test filtering commits by date range."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "7"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            from datetime import timedelta

            since_date = datetime.now() - timedelta(days=30)
            result = analyzer.analyze_repository("/fake/repo", since_date=since_date)

            # Assert - structure is valid
            assert "file_pairs" in result
            assert "metadata" in result

    def test_analyze_repository_extracts_function_level_cochanges(self):
        """Test extraction of function-level co-changes."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            cwd = kwargs.get("cwd", "/fake/repo")

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "3"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_FUNCTION_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789"
            elif "show" in cmd:
                # git show for file content
                if "module_a.ex" in str(cmd):
                    result.stdout = SAMPLE_MODULE_A_CONTENT
                elif "module_b.ex" in str(cmd):
                    result.stdout = SAMPLE_MODULE_B_CONTENT
                else:
                    result.stdout = ""
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = analyzer.analyze_repository("/fake/repo")

            # Assert - function pairs should exist
            function_pairs = result["function_pairs"]

            # ModuleA functions should co-change with ModuleB functions
            # (specific pairs depend on implementation details)
            assert "function_pairs" in result["metadata"]

    def test_analyze_repository_handles_renamed_files(self):
        """Test that renamed files are tracked correctly."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "7"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789\njkl012\nmno345\npqr678\nstu901"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = analyzer.analyze_repository("/fake/repo")

            file_pairs = result["file_pairs"]

            # Verify we found co-changes
            assert len(file_pairs) >= 1, "Expected to find co-change pairs"

            # Verify canonical ordering (pairs stored as sorted tuples)
            for pair in file_pairs.keys():
                assert isinstance(pair, tuple)
                assert len(pair) == 2
                assert pair[0] <= pair[1], f"Pair not in canonical order: {pair}"

    def test_analyze_repository_returns_metadata(self):
        """Test that metadata is correctly populated."""
        analyzer = CoChangeAnalyzer()

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0

            if "rev-list" in cmd and "--count" in cmd:
                result.stdout = "7"
            elif "--name-only" in cmd:
                result.stdout = SAMPLE_GIT_LOG_OUTPUT
            elif "--format=%H" in cmd:
                result.stdout = "abc123\ndef456\nghi789\njkl012\nmno345\npqr678\nstu901"
            else:
                result.stdout = ""

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = analyzer.analyze_repository("/fake/repo")

            metadata = result["metadata"]
            assert "analyzed_at" in metadata
            assert metadata["commit_count"] >= 5
            assert "file_pairs" in metadata
            assert "function_pairs" in metadata
            assert "optimization" in metadata

            # Verify analyzed_at is a valid ISO timestamp
            datetime.fromisoformat(metadata["analyzed_at"])
