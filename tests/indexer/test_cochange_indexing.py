"""Tests for co-change data in index schema."""

import json

import pytest

from cicada.indexer import ElixirIndexer


class TestCoChangeIndexing:
    """Test suite for co-change data in index."""

    def test_index_includes_cochange_metadata_at_root(self, git_bundle_repo, tmp_path):
        """Test that index includes cochange_metadata at root level."""
        # Use bundle which has known co-change patterns
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Act
        indexer.index_repository(
            repo_path=str(git_bundle_repo), output_path=str(output_path), extract_cochange=True
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
        assert metadata["commit_count"] >= 5

    def test_modules_have_cochange_files_array(self, git_bundle_repo, tmp_path):
        """Test that modules have cochange_files array."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(git_bundle_repo), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # Auth and Credentials modules should exist in bundle
        if "Auth" in index["modules"]:
            module_auth = index["modules"]["Auth"]
            assert "cochange_files" in module_auth

        if "Credentials" in index["modules"]:
            module_creds = index["modules"]["Credentials"]
            assert "cochange_files" in module_creds

    def test_functions_have_cochange_functions_array(self, git_bundle_repo, tmp_path):
        """Test that functions have cochange_functions array."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(git_bundle_repo), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # ModuleA and ModuleB exist in bundle with functions
        if "ModuleA" in index["modules"]:
            module_a = index["modules"]["ModuleA"]
            for func in module_a.get("functions", []):
                assert "cochange_functions" in func

    def test_cochange_counts_are_accurate(self, git_bundle_repo, tmp_path):
        """Test that co-change counts are accurate with known pattern from bundle."""
        # The bundle has known co-change patterns:
        # - auth.ex and credentials.ex co-change 4 times (commits 1-4)
        # - auth.ex and logger.ex co-change 2 times (commits 5-6)
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(git_bundle_repo), output_path=str(output_path), extract_cochange=True
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # Auth module should have co-change data
        module_auth = index["modules"]["Auth"]
        assert "cochange_files" in module_auth
        assert len(module_auth["cochange_files"]) > 0

        # Auth should co-change with credentials.ex (4 times in bundle, >= min_count=2)
        cochange_creds = next(
            (cf for cf in module_auth["cochange_files"] if "credentials.ex" in cf["file"]), None
        )
        assert cochange_creds is not None
        assert cochange_creds["count"] >= 2  # At least min_count threshold

    def test_index_without_cochange_has_no_cochange_fields(self, git_bundle_repo, tmp_path):
        """Test that index without extract_cochange doesn't have co-change fields."""
        # Act - index WITHOUT extract_cochange
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(git_bundle_repo),
            output_path=str(output_path),
            extract_cochange=False,  # Disabled
        )

        # Assert
        with open(output_path) as f:
            index = json.load(f)

        # Should NOT have cochange_metadata
        assert "cochange_metadata" not in index

        # Modules should NOT have cochange_files
        for module in index["modules"].values():
            if isinstance(module, dict):
                assert "cochange_files" not in module

    def test_cochange_handles_repo_gracefully(self, git_bundle_repo, tmp_path):
        """Test that co-change analysis handles various repo states gracefully."""
        # Act - index with cochange enabled
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"
        indexer.index_repository(
            repo_path=str(git_bundle_repo), output_path=str(output_path), extract_cochange=True
        )

        # Assert - should not crash and have valid structure
        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" in index
        assert index["cochange_metadata"]["commit_count"] > 0
        assert index["cochange_metadata"]["file_pairs"] >= 0

        # All modules should have cochange_files array (even if empty)
        for module in index["modules"].values():
            if isinstance(module, dict):
                assert "cochange_files" in module
                assert isinstance(module["cochange_files"], list)
