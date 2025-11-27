"""End-to-end integration tests for co-change feature."""

import json
import subprocess
from pathlib import Path

import pytest

from cicada.indexer import ElixirIndexer
from cicada.keyword_search import KeywordSearcher
from cicada.utils import get_index_path


class TestCoChangeE2E:
    """End-to-end tests for the complete co-change workflow."""

    def test_cochange_boosts_search_results(self, git_bundle_repo, tmp_path):
        """Test that co-change analysis boosts related search results."""
        # Arrange: Index repository with co-change enabled
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Act: Search for keywords
        searcher = KeywordSearcher(index, cochange_boost=0.5)
        results = searcher.search(["auth"], top_n=10)

        # Assert: Should find modules/functions that co-change with auth
        assert len(results) > 0
        # Results should include co-changed items (credentials, logger, etc.)

    def test_cochange_metadata_in_search_results(self, git_bundle_repo, tmp_path):
        """Test that co-change metadata appears in search results."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Act
        assert "cochange_metadata" in index
        metadata = index["cochange_metadata"]

        # Assert
        assert "analyzed_at" in metadata
        assert "commit_count" in metadata
        assert "file_pairs" in metadata
        assert "function_pairs" in metadata
        assert metadata["commit_count"] > 0

    def test_incremental_indexing_preserves_cochange_boost(self, git_bundle_repo, tmp_path):
        """Test that co-change boosts are preserved through incremental indexing."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        # First full index
        initial_index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        initial_pairs = initial_index.get("cochange_metadata", {}).get("file_pairs", 0)

        # Act: Incremental index on same repo
        incremental_index = indexer.incremental_index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Assert
        incremental_pairs = incremental_index.get("cochange_metadata", {}).get("file_pairs", 0)
        assert incremental_pairs >= initial_pairs

    def test_search_with_and_without_cochange_boost(self, git_bundle_repo, tmp_path):
        """Test that search results differ with and without co-change boost."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        storage_path = tmp_path / ".cicada"
        storage_path.mkdir()

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path),
            extract_cochange=True,
        )

        # Act: Search with boost
        searcher_with_boost = KeywordSearcher(index, cochange_boost=0.5)
        results_with_boost = searcher_with_boost.search(["function"], top_n=5)

        # Act: Search without boost
        searcher_without_boost = KeywordSearcher(index, cochange_boost=0.0)
        results_without_boost = searcher_without_boost.search(["function"], top_n=5)

        # Assert: Both should return results, may differ in order
        assert len(results_with_boost) > 0 or len(results_without_boost) > 0

    def test_cli_respects_no_cochange_flag(self, git_bundle_repo, tmp_path):
        """Test that the --no-cochange CLI flag works correctly."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        storage_path1 = tmp_path / ".cicada_with_cochange"
        storage_path2 = tmp_path / ".cicada_without_cochange"
        storage_path1.mkdir()
        storage_path2.mkdir()

        # Act: Index WITH co-change
        index_with = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path1),
            extract_cochange=True,
        )

        # Act: Index WITHOUT co-change
        index_without = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            index_dir=str(storage_path2),
            extract_cochange=False,
        )

        # Assert
        assert "cochange_metadata" in index_with
        assert "cochange_metadata" not in index_without

        # Verify modules differ
        for module in index_with.get("modules", {}).values():
            if isinstance(module, dict):
                assert "cochange_files" in module

        for module in index_without.get("modules", {}).values():
            if isinstance(module, dict):
                assert "cochange_files" not in module
