"""Tests for cicada/query/types.py"""

from datetime import datetime, timezone

import pytest

from cicada.query.types import FilterConfig, QueryOptions, SearchResult


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_is_function_returns_true_for_function(self):
        """Test is_function() returns True for function type."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
        )

        assert result.is_function() is True
        assert result.is_module() is False

    def test_is_module_returns_true_for_module(self):
        """Test is_module() returns True for module type."""
        result = SearchResult(
            type="module",
            name="MyModule",
            module="MyModule",
            file="lib/my_module.ex",
            line=1,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
        )

        assert result.is_module() is True
        assert result.is_function() is False

    def test_is_public_returns_true_for_def_visibility(self):
        """Test is_public() returns True for public functions."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            visibility="def",
        )

        assert result.is_public() is True
        assert result.is_private() is False

    def test_is_private_returns_true_for_defp_visibility(self):
        """Test is_private() returns True for private functions."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            visibility="defp",
        )

        assert result.is_private() is True
        assert result.is_public() is False

    def test_is_public_returns_true_for_modules(self):
        """Test is_public() always returns True for modules."""
        result = SearchResult(
            type="module",
            name="MyModule",
            module="MyModule",
            file="lib/my_module.ex",
            line=1,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
        )

        # Modules are considered "public" for filtering purposes
        assert result.is_public() is True
        assert result.is_private() is False

    def test_get_last_modified_returns_none_when_not_set(self):
        """Test get_last_modified() returns None when timestamp not set."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
        )

        assert result.get_last_modified() is None

    def test_get_last_modified_parses_iso_format_with_z(self):
        """Test get_last_modified() parses ISO format with Z suffix."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            last_modified_at="2024-01-15T10:30:00Z",
        )

        dt = result.get_last_modified()

        assert dt is not None
        assert dt == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_get_last_modified_parses_iso_format_with_timezone(self):
        """Test get_last_modified() parses ISO format with timezone offset."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            last_modified_at="2024-01-15T10:30:00+00:00",
        )

        dt = result.get_last_modified()

        assert dt is not None
        assert dt == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_get_last_modified_returns_none_for_invalid_format(self):
        """Test get_last_modified() returns None for invalid timestamp."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            last_modified_at="invalid-timestamp",
        )

        assert result.get_last_modified() is None

    def test_to_dict_includes_all_basic_fields(self):
        """Test to_dict() includes all basic SearchResult fields."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test", "keyword"],
            pattern_match=True,
            doc="Test documentation",
            keyword_sources={"test": "docs", "keyword": "strings"},
        )

        d = result.to_dict()

        assert d["type"] == "function"
        assert d["name"] == "MyModule.my_func"
        assert d["module"] == "MyModule"
        assert d["file"] == "lib/my_module.ex"
        assert d["line"] == 42
        assert d["score"] == 0.9
        assert d["confidence"] == 0.8
        assert d["matched_keywords"] == ["test", "keyword"]
        assert d["pattern_match"] is True
        assert d["doc"] == "Test documentation"
        assert d["keyword_sources"] == {"test": "docs", "keyword": "strings"}

    def test_to_dict_includes_function_specific_fields(self):
        """Test to_dict() includes function-specific fields."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            function="my_func",
            arity=2,
            signature="my_func(arg1, arg2)",
            visibility="def",
            last_modified_at="2024-01-15T10:30:00Z",
            last_modified_sha="abc123",
            last_modified_pr=456,
        )

        d = result.to_dict()

        assert d["function"] == "my_func"
        assert d["arity"] == 2
        assert d["signature"] == "my_func(arg1, arg2)"
        assert d["visibility"] == "def"
        assert d["last_modified_at"] == "2024-01-15T10:30:00Z"
        assert d["last_modified_sha"] == "abc123"
        assert d["last_modified_pr"] == 456

    def test_to_dict_excludes_none_function_fields(self):
        """Test to_dict() excludes function fields when they are None."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            function=None,
            arity=None,
            signature=None,
            visibility=None,
        )

        d = result.to_dict()

        assert "function" not in d
        assert "arity" not in d
        assert "signature" not in d
        assert "visibility" not in d

    def test_to_dict_includes_statistical_scoring_fields(self):
        """Test to_dict() includes statistical scoring fields."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            z_score=1.5,
            percentile=85.5,
            normalized_score=0.75,
            tier="high",
            tier_label="High Relevance",
            tier_description="Highly relevant results",
            tier_rank=1,
        )

        d = result.to_dict()

        assert d["z_score"] == 1.5
        assert d["percentile"] == 85.5
        assert d["normalized_score"] == 0.75
        assert d["tier"] == "high"
        assert d["tier_label"] == "High Relevance"
        assert d["tier_description"] == "Highly relevant results"
        assert d["tier_rank"] == 1

    def test_to_dict_excludes_none_statistical_fields(self):
        """Test to_dict() excludes statistical fields when they are None."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
        )

        d = result.to_dict()

        assert "z_score" not in d
        assert "percentile" not in d
        assert "normalized_score" not in d
        assert "tier" not in d
        assert "tier_label" not in d
        assert "tier_description" not in d
        assert "tier_rank" not in d

    def test_to_dict_excludes_none_doc_field(self):
        """Test to_dict() excludes doc when it is None."""
        result = SearchResult(
            type="function",
            name="MyModule.my_func",
            module="MyModule",
            file="lib/my_module.ex",
            line=42,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            doc=None,
        )

        d = result.to_dict()

        assert "doc" not in d

    def test_to_dict_for_module_type(self):
        """Test to_dict() for module results doesn't include function fields."""
        result = SearchResult(
            type="module",
            name="MyModule",
            module="MyModule",
            file="lib/my_module.ex",
            line=1,
            score=0.9,
            confidence=0.8,
            matched_keywords=["test"],
            pattern_match=False,
            doc="Module documentation",
        )

        d = result.to_dict()

        # Module should not have function-specific fields
        assert d["type"] == "module"
        assert "function" not in d
        assert "arity" not in d
        assert "visibility" not in d


class TestQueryOptions:
    """Test QueryOptions dataclass."""

    def test_to_filter_config_converts_all_fields(self):
        """Test to_filter_config() converts all relevant fields."""
        options = QueryOptions(
            scope="public",
            recent=True,
            filter_type="functions",
            match_source="docs",
            max_results=20,
            path_pattern="lib/**/*.ex",
            arity=2,
            show_snippets=True,
        )

        config = options.to_filter_config()

        assert isinstance(config, FilterConfig)
        assert config.scope == "public"
        assert config.recent is True
        assert config.filter_type == "functions"
        assert config.match_source == "docs"
        assert config.path_pattern == "lib/**/*.ex"
        assert config.arity == 2

    def test_to_filter_config_uses_defaults(self):
        """Test to_filter_config() uses default values correctly."""
        options = QueryOptions()

        config = options.to_filter_config()

        assert config.scope == "all"
        assert config.recent is False
        assert config.filter_type == "all"
        assert config.match_source == "all"
        assert config.path_pattern is None
        assert config.arity is None

    def test_query_options_defaults(self):
        """Test QueryOptions has correct default values."""
        options = QueryOptions()

        assert options.scope == "all"
        assert options.recent is False
        assert options.filter_type == "all"
        assert options.match_source == "all"
        assert options.max_results == 10
        assert options.path_pattern is None
        assert options.arity is None
        assert options.show_snippets is False


class TestFilterConfig:
    """Test FilterConfig dataclass."""

    def test_filter_config_defaults(self):
        """Test FilterConfig has correct default values."""
        config = FilterConfig()

        assert config.scope == "all"
        assert config.recent is False
        assert config.filter_type == "all"
        assert config.match_source == "all"
        assert config.path_pattern is None
        assert config.arity is None

    def test_filter_config_with_custom_values(self):
        """Test FilterConfig with custom values."""
        config = FilterConfig(
            scope="private",
            recent=True,
            filter_type="modules",
            match_source="strings",
            path_pattern="test/**/*.exs",
            arity=3,
        )

        assert config.scope == "private"
        assert config.recent is True
        assert config.filter_type == "modules"
        assert config.match_source == "strings"
        assert config.path_pattern == "test/**/*.exs"
        assert config.arity == 3
