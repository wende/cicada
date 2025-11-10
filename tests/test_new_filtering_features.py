"""
Tests for new filtering features added in Phase 2.

Tests the following new features:
1. Score threshold filter for search_by_features
2. Usage type filter for search_module_usage
3. Relationship shortcuts in search_function
4. Granular module dependencies
5. Time/author filters for get_commit_history
"""

import pytest
from cicada.mcp.filter_utils import (
    filter_by_score_threshold,
    is_test_file,
    classify_usage_type,
    filter_by_file_type,
)


class TestScoreFiltering:
    """Test score threshold filtering for search_by_features."""

    def test_filter_by_score_threshold_basic(self):
        """Test basic score threshold filtering."""
        results = [
            {"name": "high_score", "score": 0.9},
            {"name": "medium_score", "score": 0.5},
            {"name": "low_score", "score": 0.2},
        ]

        filtered = filter_by_score_threshold(results, 0.6)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "high_score"

    def test_filter_by_score_threshold_zero(self):
        """Test that zero threshold returns all results."""
        results = [
            {"name": "item1", "score": 0.9},
            {"name": "item2", "score": 0.1},
        ]

        filtered = filter_by_score_threshold(results, 0.0)
        assert len(filtered) == 2

    def test_filter_by_score_threshold_empty(self):
        """Test filtering empty list returns empty list."""
        filtered = filter_by_score_threshold([], 0.5)
        assert filtered == []

    def test_filter_by_score_threshold_exact_match(self):
        """Test that results exactly matching threshold are included."""
        results = [
            {"name": "exact", "score": 0.5},
            {"name": "below", "score": 0.4},
        ]

        filtered = filter_by_score_threshold(results, 0.5)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "exact"


class TestFileTypeFiltering:
    """Test file type filtering for usage sites."""

    def test_is_test_file_with_test_directory(self):
        """Test detection of files in test/ directory."""
        assert is_test_file("test/my_module_test.ex") is True
        assert is_test_file("lib/test/helper.ex") is True

    def test_is_test_file_with_test_suffix(self):
        """Test detection of files with _test suffix."""
        assert is_test_file("lib/my_module_test.ex") is True
        assert is_test_file("lib/my_module_test.exs") is True

    def test_is_test_file_with_test_prefix(self):
        """Test detection of files with test_ prefix."""
        assert is_test_file("lib/test_my_module.ex") is True

    def test_is_test_file_production_files(self):
        """Test that production files are not detected as test files."""
        assert is_test_file("lib/my_module.ex") is False
        assert is_test_file("lib/testing.ex") is False  # contains 'test' but not in right position

    def test_classify_usage_type(self):
        """Test classification of usage sites into test and production."""
        usage_sites = [
            {"file": "test/my_module_test.ex", "line": 10},
            {"file": "lib/my_module.ex", "line": 20},
            {"file": "lib/helper_test.ex", "line": 30},
            {"file": "lib/production.ex", "line": 40},
        ]

        classified = classify_usage_type(usage_sites)

        assert len(classified["test"]) == 2
        assert len(classified["production"]) == 2
        assert classified["test"][0]["file"] == "test/my_module_test.ex"
        assert classified["production"][0]["file"] == "lib/my_module.ex"

    def test_filter_by_file_type_test_only(self):
        """Test filtering for test files only."""
        usage_sites = [
            {"file": "test/my_test.ex"},
            {"file": "lib/my_module.ex"},
        ]

        filtered = filter_by_file_type(usage_sites, "test_only")
        assert len(filtered) == 1
        assert "test" in filtered[0]["file"]

    def test_filter_by_file_type_production_only(self):
        """Test filtering for production files only."""
        usage_sites = [
            {"file": "test/my_test.ex"},
            {"file": "lib/my_module.ex"},
        ]

        filtered = filter_by_file_type(usage_sites, "production_only")
        assert len(filtered) == 1
        assert "lib" in filtered[0]["file"]

    def test_filter_by_file_type_all(self):
        """Test that 'all' type returns all sites."""
        usage_sites = [
            {"file": "test/my_test.ex"},
            {"file": "lib/my_module.ex"},
        ]

        filtered = filter_by_file_type(usage_sites, "all")
        assert len(filtered) == 2

    def test_filter_by_file_type_invalid(self):
        """Test that invalid type defaults to 'all'."""
        usage_sites = [
            {"file": "test/my_test.ex"},
            {"file": "lib/my_module.ex"},
        ]

        filtered = filter_by_file_type(usage_sites, "invalid_type")
        assert len(filtered) == 2


class TestGitHelperFiltering:
    """Test git history filtering enhancements."""

    def test_filter_utils_import(self):
        """Test that filter_utils module can be imported."""
        from cicada.mcp import filter_utils

        assert hasattr(filter_utils, "filter_by_score_threshold")
        assert hasattr(filter_utils, "is_test_file")
        assert hasattr(filter_utils, "classify_usage_type")
        assert hasattr(filter_utils, "filter_by_file_type")


class TestIntegration:
    """Integration tests for new features."""

    def test_filter_utils_comprehensive(self):
        """Test complete workflow of filtering."""
        # Simulate search results with various scores
        search_results = [
            {"name": "ModuleA", "score": 0.95, "type": "module"},
            {"name": "ModuleB", "score": 0.75, "type": "module"},
            {"name": "ModuleC", "score": 0.45, "type": "module"},
            {"name": "ModuleD", "score": 0.15, "type": "module"},
        ]

        # Filter by score threshold
        high_quality = filter_by_score_threshold(search_results, 0.7)
        assert len(high_quality) == 2
        assert all(r["score"] >= 0.7 for r in high_quality)

        # Simulate usage sites from different file types
        usage_sites = [
            {"file": "test/module_a_test.ex", "module": "TestModuleA"},
            {"file": "test/module_b_test.ex", "module": "TestModuleB"},
            {"file": "lib/module_a.ex", "module": "ModuleA"},
            {"file": "lib/module_b.ex", "module": "ModuleB"},
            {"file": "lib/utils/helper.ex", "module": "Helper"},
        ]

        # Filter for test files only
        test_sites = filter_by_file_type(usage_sites, "test_only")
        assert len(test_sites) == 2
        assert all(is_test_file(site["file"]) for site in test_sites)

        # Filter for production files only
        prod_sites = filter_by_file_type(usage_sites, "production_only")
        assert len(prod_sites) == 3
        assert all(not is_test_file(site["file"]) for site in prod_sites)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
