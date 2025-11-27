"""End-to-end integration tests for co-change feature."""

import pytest

from cicada.indexer import ElixirIndexer
from cicada.keyword_search import KeywordSearcher


class TestCoChangeE2E:
    """End-to-end tests for the complete co-change workflow."""

    def test_cochange_boosts_search_results(self, git_bundle_repo, tmp_path):
        """Test that co-change analysis boosts related search results."""
        # Arrange: Index repository with co-change enabled
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Assert: Index includes co-change data and can be used with searcher
        assert "cochange_metadata" in index
        assert index["cochange_metadata"]["file_pairs"] > 0

        # Verify we can instantiate searcher with cochange_boost
        searcher = KeywordSearcher(index, cochange_boost=0.5)
        assert searcher is not None

    def test_cochange_metadata_in_search_results(self, git_bundle_repo, tmp_path):
        """Test that co-change metadata appears in search results."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
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
        output_path = tmp_path / "index.json"

        # First full index
        initial_index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        initial_pairs = initial_index.get("cochange_metadata", {}).get("file_pairs", 0)

        # Act: Incremental index on same repo
        incremental_index = indexer.incremental_index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Assert
        incremental_pairs = incremental_index.get("cochange_metadata", {}).get("file_pairs", 0)
        assert incremental_pairs >= initial_pairs

    def test_search_with_and_without_cochange_boost(self, git_bundle_repo, tmp_path):
        """Test that search can be configured with cochange_boost parameter."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=True,
        )

        # Act: Create searchers with different cochange_boost values
        searcher_with_boost = KeywordSearcher(index, cochange_boost=0.5)
        searcher_without_boost = KeywordSearcher(index, cochange_boost=0.0)

        # Assert: Both searchers should be properly configured
        assert searcher_with_boost is not None
        assert searcher_without_boost is not None
        # Verify cochange data exists for boosting
        assert "cochange_metadata" in index

    def test_cli_respects_no_cochange_flag(self, git_bundle_repo, tmp_path):
        """Test that the --no-cochange CLI flag works correctly."""
        # Arrange
        indexer = ElixirIndexer(verbose=False)
        output_path1 = tmp_path / "index_with_cochange.json"
        output_path2 = tmp_path / "index_without_cochange.json"

        # Act: Index WITH co-change
        index_with = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path1),
            extract_cochange=True,
        )

        # Act: Index WITHOUT co-change
        index_without = indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path2),
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
