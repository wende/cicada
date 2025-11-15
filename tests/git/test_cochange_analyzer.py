"""Tests for co-change analysis from git history."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from cicada.git.cochange_analyzer import CoChangeAnalyzer


class TestCoChangeAnalyzer:
    """Test suite for CoChangeAnalyzer."""

    def test_analyze_repository_returns_empty_for_no_commits(self, tmp_path):
        """Test that analyzing a repo with no commits returns empty results."""
        # Arrange: Create empty git repo
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert
        assert result["file_pairs"] == {}
        assert result["function_pairs"] == {}
        assert result["metadata"]["commit_count"] == 0

    def test_analyze_repository_extracts_file_level_cochanges(self, tmp_path):
        """Test extraction of file-level co-changes from git history."""
        # Arrange: Create repo with known co-change pattern
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create files that will be changed together
        file_a = repo_path / "lib" / "module_a.ex"
        file_b = repo_path / "lib" / "module_b.ex"
        file_c = repo_path / "lib" / "module_c.ex"

        file_a.parent.mkdir(parents=True, exist_ok=True)

        # Commit 1: A and B together
        file_a.write_text("defmodule A do\nend")
        file_b.write_text("defmodule B do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add A and B"], cwd=repo_path, check=True, capture_output=True
        )

        # Commit 2: A and B together again
        file_a.write_text("defmodule A do\n  def foo, do: :ok\nend")
        file_b.write_text("defmodule B do\n  def bar, do: :ok\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update A and B"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 3: A and C together
        file_a.write_text("defmodule A do\n  def foo, do: :ok\n  def baz, do: :ok\nend")
        file_c.write_text("defmodule C do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update A and add C"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert
        file_pairs = result["file_pairs"]

        # With canonical ordering, pairs are stored in sorted (alphabetical) order
        # A and B should have co-changed 2 times (only canonical ordering stored)
        assert file_pairs.get(("lib/module_a.ex", "lib/module_b.ex"), 0) == 2

        # A and C should have co-changed 1 time (only canonical ordering stored)
        assert file_pairs.get(("lib/module_a.ex", "lib/module_c.ex"), 0) == 1

        # Verify bidirectional lookups don't exist (we only store canonical form)
        assert ("lib/module_b.ex", "lib/module_a.ex") not in file_pairs
        assert ("lib/module_c.ex", "lib/module_a.ex") not in file_pairs

        # Metadata
        assert result["metadata"]["commit_count"] == 3
        assert result["metadata"]["file_pairs"] == 2  # Exactly 2 unique pairs

    def test_analyze_repository_handles_single_file_commits(self, tmp_path):
        """Test that commits with only one file don't create co-change entries."""
        # Arrange
        repo_path = tmp_path / "single_file_repo"
        repo_path.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create and commit single file
        file_a = repo_path / "lib" / "solo.ex"
        file_a.parent.mkdir(parents=True, exist_ok=True)
        file_a.write_text("defmodule Solo do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add solo file"], cwd=repo_path, check=True, capture_output=True
        )

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert - no co-changes for single-file commit
        assert result["file_pairs"] == {}
        assert result["metadata"]["commit_count"] == 1

    def test_analyze_repository_respects_minimum_count_threshold(self, tmp_path):
        """Test filtering by minimum co-change count."""
        # Arrange: Create repo with different co-change frequencies
        repo_path = tmp_path / "threshold_repo"
        repo_path.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = repo_path / "a.ex"
        file_b = repo_path / "b.ex"
        file_c = repo_path / "c.ex"

        # A+B changed together 3 times
        for i in range(3):
            file_a.write_text(f"defmodule A do\n  # version {i}\nend")
            file_b.write_text(f"defmodule B do\n  # version {i}\nend")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update A+B {i}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        # A+C changed together 1 time
        file_a.write_text("defmodule A do\n  # final\nend")
        file_c.write_text("defmodule C do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update A+C"], cwd=repo_path, check=True, capture_output=True
        )

        analyzer = CoChangeAnalyzer()

        # Act - filter for minimum 2 co-changes
        result = analyzer.analyze_repository(str(repo_path), min_count=2)

        # Assert - only A+B should appear (3 times >= 2)
        file_pairs = result["file_pairs"]
        assert file_pairs.get(("a.ex", "b.ex"), 0) == 3
        # A+C should be filtered out (1 time < 2)
        assert ("a.ex", "c.ex") not in file_pairs
        assert ("c.ex", "a.ex") not in file_pairs

    def test_analyze_repository_respects_date_range(self, tmp_path):
        """Test filtering commits by date range."""
        # Arrange
        repo_path = tmp_path / "date_repo"
        repo_path.mkdir()

        import subprocess
        import os

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = repo_path / "a.ex"
        file_b = repo_path / "b.ex"

        # Old commit (60 days ago)
        file_a.write_text("v1")
        file_b.write_text("v1")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)

        # Create commit with old date using environment variables
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
        old_env = os.environ.copy()
        old_env["GIT_AUTHOR_DATE"] = old_date
        old_env["GIT_COMMITTER_DATE"] = old_date
        subprocess.run(
            ["git", "commit", "-m", "Old commit"],
            cwd=repo_path,
            env=old_env,
            check=True,
            capture_output=True,
        )

        # Recent commit (now)
        file_a.write_text("v2")
        file_b.write_text("v2")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Recent commit"], cwd=repo_path, check=True, capture_output=True
        )

        analyzer = CoChangeAnalyzer()

        # Act - only analyze last 30 days
        since_date = datetime.now() - timedelta(days=30)
        result = analyzer.analyze_repository(str(repo_path), since_date=since_date)

        # Assert - only recent commit counted
        assert result["metadata"]["commit_count"] == 1
        file_pairs = result["file_pairs"]
        assert file_pairs.get(("a.ex", "b.ex"), 0) == 1

    def test_analyze_repository_extracts_function_level_cochanges(self, tmp_path):
        """Test extraction of function-level co-changes."""
        # Arrange: Create repo with Elixir functions that change together
        repo_path = tmp_path / "func_repo"
        repo_path.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create files with functions
        file_a = repo_path / "lib" / "module_a.ex"
        file_b = repo_path / "lib" / "module_b.ex"
        file_a.parent.mkdir(parents=True, exist_ok=True)

        # Initial commit with functions
        file_a.write_text(
            """defmodule ModuleA do
  def func_one(x) do
    x + 1
  end

  def func_two(x) do
    x + 2
  end
end
"""
        )
        file_b.write_text(
            """defmodule ModuleB do
  def func_three(x) do
    x + 3
  end
end
"""
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial functions"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 2: Modify func_one and func_three together
        file_a.write_text(
            """defmodule ModuleA do
  def func_one(x) do
    x + 10  # changed
  end

  def func_two(x) do
    x + 2
  end
end
"""
        )
        file_b.write_text(
            """defmodule ModuleB do
  def func_three(x) do
    x + 30  # changed
  end
end
"""
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update func_one and func_three"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 3: Modify func_one and func_three again
        file_a.write_text(
            """defmodule ModuleA do
  def func_one(x) do
    x + 100  # changed again
  end

  def func_two(x) do
    x + 2
  end
end
"""
        )
        file_b.write_text(
            """defmodule ModuleB do
  def func_three(x) do
    x + 300  # changed again
  end
end
"""
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update func_one and func_three again"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert
        function_pairs = result["function_pairs"]

        # func_one and func_three should have co-changed 3 times
        # (initial commit when both created + 2 modification commits)
        # With canonical ordering, pairs are stored alphabetically sorted
        canonical_key = tuple(sorted(["ModuleA.func_one/1", "ModuleB.func_three/1"]))
        assert function_pairs.get(canonical_key, 0) == 3

        # func_two appears in co-changes with func_one (same file) and func_three (initial commit)
        # but should have co-changed 3 times (all 3 commits where module_a.ex was modified)
        assert function_pairs.get(("ModuleA.func_one/1", "ModuleA.func_two/1"), 0) == 3

    def test_analyze_repository_handles_renamed_files(self, tmp_path):
        """Test that renamed files are tracked correctly."""
        # Arrange
        repo_path = tmp_path / "rename_repo"
        repo_path.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial files
        file_a = repo_path / "old_name.ex"
        file_b = repo_path / "companion.ex"

        file_a.write_text("defmodule Old do\nend")
        file_b.write_text("defmodule Companion do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        # Rename file_a and modify both
        subprocess.run(
            ["git", "mv", "old_name.ex", "new_name.ex"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        file_new = repo_path / "new_name.ex"
        file_new.write_text("defmodule New do\n  # renamed\nend")
        file_b.write_text("defmodule Companion do\n  # updated\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Rename and update"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert - should track the rename and show co-change
        file_pairs = result["file_pairs"]
        # Should show co-change with new name
        assert (
            file_pairs.get(("new_name.ex", "companion.ex"), 0) >= 1
            or file_pairs.get(("companion.ex", "new_name.ex"), 0) >= 1
        )

    def test_analyze_repository_returns_metadata(self, tmp_path):
        """Test that metadata is correctly populated."""
        # Arrange
        repo_path = tmp_path / "meta_repo"
        repo_path.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = repo_path / "a.ex"
        file_b = repo_path / "b.ex"

        file_a.write_text("v1")
        file_b.write_text("v1")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Commit 1"], cwd=repo_path, check=True, capture_output=True
        )

        analyzer = CoChangeAnalyzer()

        # Act
        result = analyzer.analyze_repository(str(repo_path))

        # Assert
        metadata = result["metadata"]
        assert "analyzed_at" in metadata
        assert metadata["commit_count"] == 1
        assert "file_pairs" in metadata
        assert "function_pairs" in metadata

        # Verify analyzed_at is a valid ISO timestamp
        from datetime import datetime

        datetime.fromisoformat(metadata["analyzed_at"])  # Should not raise
