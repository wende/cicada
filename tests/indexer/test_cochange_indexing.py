"""Tests for co-change data in index schema."""

import pytest
import json
from pathlib import Path
from cicada.indexer import ElixirIndexer


class TestCoChangeIndexing:
    """Test suite for co-change data in index."""

    def test_index_includes_cochange_metadata_at_root(self, tmp_path):
        """Test that index includes cochange_metadata at root level."""
        # Arrange: Create a simple Elixir project with git history
        repo_path = tmp_path / "test_project"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        # Initialize git
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create module files
        (lib_dir / "module_a.ex").write_text(
            """defmodule ModuleA do
  @moduledoc \"Module A\"
  def func_a, do: :ok
end
"""
        )
        (lib_dir / "module_b.ex").write_text(
            """defmodule ModuleB do
  @moduledoc \"Module B\"
  def func_b, do: :ok
end
"""
        )

        # Commit both files together
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add modules"], cwd=repo_path, check=True, capture_output=True
        )

        # Index with co-change enabled
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Act
        indexer.index_repository(
            repo_path=str(repo_path), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" in index
        metadata = index["cochange_metadata"]
        assert "analyzed_at" in metadata
        assert "commit_count" in metadata
        assert "file_pairs" in metadata
        assert "function_pairs" in metadata
        assert metadata["commit_count"] >= 1

    def test_modules_have_cochange_files_array(self, tmp_path):
        """Test that modules have cochange_files array."""
        # Arrange
        repo_path = tmp_path / "test_project"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = lib_dir / "module_a.ex"
        file_b = lib_dir / "module_b.ex"

        # Commit 1: Both files together
        file_a.write_text("defmodule ModuleA do\nend")
        file_b.write_text("defmodule ModuleB do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        # Commit 2: Modify both together
        file_a.write_text("defmodule ModuleA do\n  def foo, do: :ok\nend")
        file_b.write_text("defmodule ModuleB do\n  def bar, do: :ok\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update both"], cwd=repo_path, check=True, capture_output=True
        )

        # Act
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(repo_path), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # Both modules should have co-change information
        assert "ModuleA" in index["modules"]
        assert "ModuleB" in index["modules"]

        module_a = index["modules"]["ModuleA"]
        module_b = index["modules"]["ModuleB"]

        # Check cochange_files exists
        assert "cochange_files" in module_a
        assert "cochange_files" in module_b

        # ModuleA should show co-change with module_b.ex
        cochange_files_a = module_a["cochange_files"]
        assert any(cf["file"] == "lib/module_b.ex" and cf["count"] == 2 for cf in cochange_files_a)

        # ModuleB should show co-change with module_a.ex
        cochange_files_b = module_b["cochange_files"]
        assert any(cf["file"] == "lib/module_a.ex" and cf["count"] == 2 for cf in cochange_files_b)

    def test_functions_have_cochange_functions_array(self, tmp_path):
        """Test that functions have cochange_functions array."""
        # Arrange
        repo_path = tmp_path / "test_project"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = lib_dir / "module_a.ex"
        file_b = lib_dir / "module_b.ex"

        # Initial commit with functions
        file_a.write_text(
            """defmodule ModuleA do
  def func_a(x), do: x + 1
end
"""
        )
        file_b.write_text(
            """defmodule ModuleB do
  def func_b(x), do: x + 2
end
"""
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add functions"], cwd=repo_path, check=True, capture_output=True
        )

        # Act
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(repo_path), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        module_a = index["modules"]["ModuleA"]
        module_b = index["modules"]["ModuleB"]

        # Find func_a and func_b
        func_a = next(f for f in module_a["functions"] if f["name"] == "func_a")
        func_b = next(f for f in module_b["functions"] if f["name"] == "func_b")

        # Check cochange_functions exists
        assert "cochange_functions" in func_a
        assert "cochange_functions" in func_b

        # func_a should show co-change with ModuleB.func_b/1
        cochange_funcs_a = func_a["cochange_functions"]
        assert any(
            cf["module"] == "ModuleB" and cf["function"] == "func_b" and cf["arity"] == 1
            for cf in cochange_funcs_a
        )

    def test_cochange_counts_are_accurate(self, tmp_path):
        """Test that co-change counts are accurate."""
        # Arrange: Create known co-change pattern
        repo_path = tmp_path / "test_project"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        file_a = lib_dir / "module_a.ex"
        file_b = lib_dir / "module_b.ex"
        file_c = lib_dir / "module_c.ex"

        # Commit 1: A and B together
        file_a.write_text("defmodule ModuleA do\nend")
        file_b.write_text("defmodule ModuleB do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add A and B"], cwd=repo_path, check=True, capture_output=True
        )

        # Commit 2: A and B together again
        file_a.write_text("defmodule ModuleA do\n  # v2\nend")
        file_b.write_text("defmodule ModuleB do\n  # v2\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update A and B"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 3: A and B together a third time
        file_a.write_text("defmodule ModuleA do\n  # v3\nend")
        file_b.write_text("defmodule ModuleB do\n  # v3\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update A and B again"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 4: A and C together once
        file_a.write_text("defmodule ModuleA do\n  # v4\nend")
        file_c.write_text("defmodule ModuleC do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add C with A"], cwd=repo_path, check=True, capture_output=True
        )

        # Act
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(repo_path), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        module_a = index["modules"]["ModuleA"]

        # A should co-change with B 3 times
        cochange_b = next(
            (cf for cf in module_a["cochange_files"] if "module_b.ex" in cf["file"]), None
        )
        assert cochange_b is not None
        assert cochange_b["count"] == 3

        # A should co-change with C 1 time
        cochange_c = next(
            (cf for cf in module_a["cochange_files"] if "module_c.ex" in cf["file"]), None
        )
        assert cochange_c is not None
        assert cochange_c["count"] == 1

    def test_index_without_cochange_has_no_cochange_fields(self, tmp_path):
        """Test that index without extract_cochange doesn't have co-change fields."""
        # Arrange
        repo_path = tmp_path / "test_project"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        (lib_dir / "module_a.ex").write_text("defmodule ModuleA do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add module"], cwd=repo_path, check=True, capture_output=True
        )

        # Act - index WITHOUT extract_cochange
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            extract_cochange=False,  # Disabled
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # Should NOT have cochange_metadata
        assert "cochange_metadata" not in index

        # Modules should NOT have cochange_files
        module_a = index["modules"]["ModuleA"]
        assert "cochange_files" not in module_a

    def test_empty_repo_handles_cochange_gracefully(self, tmp_path):
        """Test that empty repo with co-change enabled doesn't crash."""
        # Arrange: Empty git repo
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create a module but don't commit it
        (lib_dir / "module_a.ex").write_text("defmodule ModuleA do\nend")

        # Act
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(repo_path), output_path=str(output_path), extract_cochange=True
        )

        # Assert - should not crash, but no co-change data
        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" in index
        assert index["cochange_metadata"]["commit_count"] == 0
        assert index["cochange_metadata"]["file_pairs"] == 0

        # Module should exist but with empty co-change arrays
        module_a = index["modules"]["ModuleA"]
        assert module_a["cochange_files"] == []
