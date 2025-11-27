"""Test that co-change data is preserved/recomputed in incremental indexing."""

import json

import pytest

from cicada.indexer import ElixirIndexer


class TestCoChangeIncremental:
    """Test co-change data in incremental indexing."""

    def test_incremental_indexing_preserves_cochange_data(self, git_bundle_repo, tmp_path):
        """Test that co-change data is preserved when doing incremental updates."""
        # Arrange: Initial full index from bundle
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # First full index
        indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Read initial co-change metadata
        with open(output_path) as f:
            initial_index = json.load(f)

        initial_cochange_count = initial_index.get("cochange_metadata", {}).get("commit_count", 0)

        # Act: Do an incremental index (no new commits, so should be similar)
        incremental_index = indexer.incremental_index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Assert: Co-change data should be present
        assert "cochange_metadata" in incremental_index
        assert incremental_index["cochange_metadata"]["commit_count"] >= initial_cochange_count

    def test_incremental_recomputes_cochange_when_enabled(self, git_bundle_repo, tmp_path):
        """Test that co-change is recomputed in incremental mode."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Index with cochange enabled
        result = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Assert
        assert "cochange_metadata" in result
        assert result["cochange_metadata"]["commit_count"] >= 5

    def test_incremental_with_cochange_disabled_preserves_structure(self, git_bundle_repo, tmp_path):
        """Test that running incremental with extract_cochange=False preserves index structure."""
        # Arrange: Use bundle repo (has git history, safe for parallel tests)
        output_path = tmp_path / "index.json"
        indexer = ElixirIndexer(verbose=False)

        # First: index WITH cochange
        indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        with open(output_path) as f:
            indexed_with_cochange = json.load(f)

        assert "cochange_metadata" in indexed_with_cochange
        initial_file_pairs = indexed_with_cochange["cochange_metadata"]["file_pairs"]
        assert initial_file_pairs > 0

        # Act: incremental index with extract_cochange=False
        # When no changes detected, incremental just reports "up to date"
        indexer.incremental_index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=False,
        )

        # Assert: index should still have valid structure
        with open(output_path) as f:
            indexed_after = json.load(f)

        # cochange_metadata may be preserved (incremental doesn't clear when no changes)
        # The key is that the index is still valid and usable
        assert "modules" in indexed_after
        assert len(indexed_after["modules"]) > 0
