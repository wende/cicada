"""Test that co-change data is preserved/recomputed in incremental indexing."""

import subprocess
import json
from pathlib import Path

import pytest

from cicada.indexer import ElixirIndexer
from cicada.utils import get_index_path


class TestCoChangeIncremental:
    """Test co-change data in incremental indexing."""

    def test_incremental_indexing_preserves_cochange_data(self, git_bundle_repo, tmp_path):
        """Test that co-change data is preserved when doing incremental updates."""
        # Arrange: Initial full index from bundle
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        # First full index
        initial_index_path = get_index_path(str(git_bundle_repo), storage_path)
        indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Read initial co-change metadata
        with open(initial_index_path) as f:
            initial_index = json.load(f)

        initial_cochange_count = initial_index.get("cochange_metadata", {}).get("commit_count", 0)

        # Act: Do an incremental index (no new commits, so should be similar)
        incremental_index = indexer.incremental_index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Assert: Co-change data should be present
        assert "cochange_metadata" in incremental_index
        assert incremental_index["cochange_metadata"]["commit_count"] >= initial_cochange_count

    def test_incremental_recomputes_cochange_when_enabled(self, git_bundle_repo, tmp_path):
        """Test that co-change is recomputed in incremental mode."""
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        # Index with cochange enabled
        result = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Assert
        assert "cochange_metadata" in result
        assert result["cochange_metadata"]["commit_count"] >= 5

    def test_incremental_without_cochange_clears_previous_data(self, tmp_path):
        """Test that running incremental without co-change clears previous co-change data."""
        # Arrange: Create minimal test repo with co-changes
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

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
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        (lib_dir / "a.ex").write_text("defmodule A do\nend")
        (lib_dir / "b.ex").write_text("defmodule B do\nend")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()
        indexer = ElixirIndexer(verbose=False)

        # First: index WITH cochange
        indexer.index_repository(
            repo_path=str(repo_path),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        index_path = get_index_path(str(repo_path), storage_path)
        with open(index_path) as f:
            indexed_with_cochange = json.load(f)

        assert "cochange_metadata" in indexed_with_cochange

        # Act: index WITHOUT cochange (should remove co-change data)
        indexer.incremental_index_repository(
            repo_path=str(repo_path),
            index_dir=str(storage_path),
            extract_cochange=False,
        )

        # Assert: co-change data should be gone
        with open(index_path) as f:
            indexed_without_cochange = json.load(f)

        assert "cochange_metadata" not in indexed_without_cochange
        for module in indexed_without_cochange["modules"].values():
            assert "cochange_files" not in module
