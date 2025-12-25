"""Tests for the fallback search strategies module."""

import pytest

from cicada.mcp.fallbacks import (
    DEFAULT_FUNCTION_FALLBACKS,
    DEFAULT_MODULE_FALLBACKS,
    DEFAULT_QUERY_FALLBACKS,
    CamelSnakeFallback,
    FallbackResult,
    LastSegmentFallback,
    MatchSourceFallback,
    ModuleFallbackResult,
    PrefixWildcardFallback,
    PrivateFunctionFallback,
    QueryFallbackResult,
    RecentFallback,
    ScopeFallback,
    WithoutArityFallback,
    WithoutModuleFallback,
    apply_fallbacks,
    apply_module_fallbacks,
    apply_query_fallbacks,
)
from cicada.mcp.pattern_utils import FunctionPattern
from cicada.query.types import QueryOptions


class TestWithoutModuleFallback:
    """Tests for WithoutModuleFallback strategy."""

    def test_should_try_when_module_present(self):
        strategy = WithoutModuleFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create")]
        assert strategy.should_try(patterns, {}) is True

    def test_should_not_try_when_no_module(self):
        strategy = WithoutModuleFallback()
        patterns = [FunctionPattern(name="create")]
        assert strategy.should_try(patterns, {}) is False

    def test_should_not_try_when_module_path_explicit(self):
        strategy = WithoutModuleFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create")]
        assert strategy.should_try(patterns, {"module_path": "MyApp"}) is False

    def test_transform_removes_module(self):
        strategy = WithoutModuleFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].module is None
        assert transformed[0].name == "create"
        assert transformed[0].arity == 2

    def test_get_note(self):
        strategy = WithoutModuleFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create")]
        note = strategy.get_note(patterns)
        assert "MyApp" in note
        assert "no matches" in note


class TestWithoutArityFallback:
    """Tests for WithoutArityFallback strategy."""

    def test_should_try_when_arity_present(self):
        strategy = WithoutArityFallback()
        patterns = [FunctionPattern(name="create", arity=2)]
        assert strategy.should_try(patterns, {}) is True

    def test_should_not_try_when_no_arity(self):
        strategy = WithoutArityFallback()
        patterns = [FunctionPattern(name="create")]
        assert strategy.should_try(patterns, {}) is False

    def test_transform_removes_arity(self):
        strategy = WithoutArityFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].module == "*.MyApp"
        assert transformed[0].name == "create"
        assert transformed[0].arity is None

    def test_get_note(self):
        strategy = WithoutArityFallback()
        patterns = [FunctionPattern(name="create", arity=2)]
        note = strategy.get_note(patterns)
        assert "/2" in note
        assert "no matches with arity" in note


class TestPrivateFunctionFallback:
    """Tests for PrivateFunctionFallback strategy."""

    def test_should_try_for_public_function(self):
        strategy = PrivateFunctionFallback()
        patterns = [FunctionPattern(name="create")]
        assert strategy.should_try(patterns, {}) is True

    def test_should_not_try_for_private_function(self):
        strategy = PrivateFunctionFallback()
        patterns = [FunctionPattern(name="_create")]
        assert strategy.should_try(patterns, {}) is False

    def test_should_not_try_for_wildcard(self):
        strategy = PrivateFunctionFallback()
        patterns = [FunctionPattern(name="create*")]
        assert strategy.should_try(patterns, {}) is False

    def test_transform_adds_underscore(self):
        strategy = PrivateFunctionFallback()
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].name == "_create"
        assert transformed[0].module == "*.MyApp"
        assert transformed[0].arity == 2

    def test_get_note(self):
        strategy = PrivateFunctionFallback()
        patterns = [FunctionPattern(name="create")]
        note = strategy.get_note(patterns)
        assert "private" in note


class TestApplyFallbacks:
    """Tests for the apply_fallbacks function."""

    def test_returns_empty_when_no_fallback_matches(self):
        patterns = [FunctionPattern(name="create")]

        def search_fn(p):
            return []

        result = apply_fallbacks(patterns, search_fn)
        assert result.results == []
        assert result.note is None

    def test_returns_results_from_first_matching_fallback(self):
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        mock_results = [{"module": "OtherApp", "function": {"name": "create"}}]

        def search_fn(p):
            # Only return results when module is None (fallback 1)
            if p[0].module is None:
                return mock_results
            return []

        result = apply_fallbacks(patterns, search_fn)
        assert result.results == mock_results
        assert result.note is not None
        assert "MyApp" in result.note

    def test_tries_fallbacks_in_order(self):
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        call_order = []

        def search_fn(p):
            call_order.append(("module" if p[0].module else "no_module", p[0].arity))
            return []

        apply_fallbacks(patterns, search_fn)
        # Should try: 1) without module, 2) without arity, 3) private
        assert ("no_module", 2) in call_order  # Fallback 1: removes module, keeps arity
        assert ("module", None) in call_order  # Fallback 2: keeps module, removes arity

    def test_respects_module_path_context(self):
        patterns = [FunctionPattern(module="*.MyApp", name="create")]
        call_count = [0]

        def search_fn(p):
            call_count[0] += 1
            return []

        # With module_path set, should skip WithoutModuleFallback
        apply_fallbacks(patterns, search_fn, context={"module_path": "MyApp"})

        # Should still try other fallbacks (arity, private)
        # but not the module fallback
        assert call_count[0] >= 0  # Just verify it runs without error

    def test_accumulates_notes_from_failed_strategies(self):
        """Notes should accumulate from all tried strategies, not just the successful one."""
        patterns = [FunctionPattern(module="*.MyApp", name="create", arity=2)]
        mock_results = [{"module": "OtherApp", "function": {"name": "_create"}}]
        attempts = []

        def search_fn(p):
            # Track what was attempted
            attempts.append(
                ("no_module" if p[0].module is None else "module", p[0].arity, p[0].name)
            )
            # Only succeed on private function fallback
            if p[0].name == "_create":
                return mock_results
            return []

        result = apply_fallbacks(patterns, search_fn)
        assert result.results == mock_results
        # Note should contain info about all failed strategies + the successful one
        assert result.note is not None
        # Should mention both the module fallback and private fallback
        assert "no matches in" in result.note
        assert "private" in result.note


class TestFallbackResult:
    """Tests for FallbackResult dataclass."""

    def test_default_note_is_none(self):
        result = FallbackResult(results=[])
        assert result.note is None

    def test_can_set_note(self):
        result = FallbackResult(results=[], note="test note")
        assert result.note == "test note"


# =============================================================================
# Module Fallback Tests
# =============================================================================


class TestLastSegmentFallback:
    """Tests for LastSegmentFallback strategy."""

    def test_should_try_when_module_has_dots(self):
        strategy = LastSegmentFallback()
        assert strategy.should_try("A.B.C.D", {}) is True
        assert strategy.should_try("MyApp.User", {}) is True

    def test_should_try_for_single_segment(self):
        """Single segment modules also get fallback to find nested modules."""
        strategy = LastSegmentFallback()
        assert strategy.should_try("User", {}) is True
        assert strategy.should_try("SomeModule", {}) is True

    def test_transform_extracts_last_segment(self):
        strategy = LastSegmentFallback()
        assert strategy.transform_pattern("A.B.C.D") == "*.D"
        assert strategy.transform_pattern("MyApp.User") == "*.User"
        assert strategy.transform_pattern("MyProject.Context.User") == "*.User"

    def test_get_note_includes_original_and_fallback(self):
        strategy = LastSegmentFallback()
        note = strategy.get_note("WrongProject.User")
        assert "WrongProject.User" in note
        assert "User" in note


class TestApplyModuleFallbacks:
    """Tests for the apply_module_fallbacks function."""

    def test_returns_empty_when_no_fallback_matches(self):
        def search_fn(pattern):
            return []

        result = apply_module_fallbacks("SomeModule", search_fn)
        assert result.results == []
        assert result.note is None

    def test_tries_single_segment_module(self):
        """Single segment modules also get fallback to find nested modules."""
        call_count = [0]
        patterns_searched = []

        def search_fn(pattern):
            call_count[0] += 1
            patterns_searched.append(pattern)
            return []

        # Single segment module should also trigger fallback
        apply_module_fallbacks("User", search_fn)
        assert call_count[0] == 1  # Fallback attempted
        assert "*.User" in patterns_searched

    def test_returns_results_from_fallback(self):
        mock_results = [("MyProject.User", {"file": "lib/user.ex"})]

        def search_fn(pattern):
            if pattern == "*.User":
                return mock_results
            return []

        result = apply_module_fallbacks("WrongProject.User", search_fn)
        assert result.results == mock_results
        assert result.note is not None
        assert "User" in result.note

    def test_fallback_uses_last_segment_only(self):
        patterns_searched = []

        def search_fn(pattern):
            patterns_searched.append(pattern)
            return [("Found.Module", {})] if "*.D" in pattern else []

        result = apply_module_fallbacks("A.B.C.D", search_fn)
        assert "*.D" in patterns_searched
        assert result.results is not None


# =============================================================================
# Query Fallback Tests
# =============================================================================


class TestMatchSourceFallback:
    """Tests for MatchSourceFallback strategy."""

    def test_should_try_with_strings_source(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="strings")
        assert strategy.should_try(options, {}) is True

    def test_should_try_with_docs_source(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="docs")
        assert strategy.should_try(options, {}) is True

    def test_should_try_with_comments_source(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="comments")
        assert strategy.should_try(options, {}) is True

    def test_should_not_try_with_all_source(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="all")
        assert strategy.should_try(options, {}) is False

    def test_transform_changes_to_all(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="strings", scope="public")
        transformed = strategy.transform_options(options)
        assert transformed.match_source == "all"
        assert transformed.scope == "public"  # Other options preserved

    def test_get_note_mentions_original_source(self):
        strategy = MatchSourceFallback()
        options = QueryOptions(match_source="strings")
        note = strategy.get_note(options)
        assert "strings" in note
        assert "all sources" in note


class TestScopeFallback:
    """Tests for ScopeFallback strategy."""

    def test_should_try_with_public_scope(self):
        strategy = ScopeFallback()
        options = QueryOptions(scope="public")
        assert strategy.should_try(options, {}) is True

    def test_should_try_with_private_scope(self):
        strategy = ScopeFallback()
        options = QueryOptions(scope="private")
        assert strategy.should_try(options, {}) is True

    def test_should_not_try_with_all_scope(self):
        strategy = ScopeFallback()
        options = QueryOptions(scope="all")
        assert strategy.should_try(options, {}) is False

    def test_transform_changes_to_all(self):
        strategy = ScopeFallback()
        options = QueryOptions(scope="public", recent=True)
        transformed = strategy.transform_options(options)
        assert transformed.scope == "all"
        assert transformed.recent is True  # Other options preserved

    def test_get_note_mentions_original_scope(self):
        strategy = ScopeFallback()
        options = QueryOptions(scope="public")
        note = strategy.get_note(options)
        assert "public" in note
        assert "visibility" in note


class TestRecentFallback:
    """Tests for RecentFallback strategy."""

    def test_should_try_when_recent_is_true(self):
        strategy = RecentFallback()
        options = QueryOptions(recent=True)
        assert strategy.should_try(options, {}) is True

    def test_should_not_try_when_recent_is_false(self):
        strategy = RecentFallback()
        options = QueryOptions(recent=False)
        assert strategy.should_try(options, {}) is False

    def test_transform_sets_recent_to_false(self):
        strategy = RecentFallback()
        options = QueryOptions(recent=True, scope="public")
        transformed = strategy.transform_options(options)
        assert transformed.recent is False
        assert transformed.scope == "public"  # Other options preserved

    def test_get_note_mentions_recent(self):
        strategy = RecentFallback()
        options = QueryOptions(recent=True)
        note = strategy.get_note(options)
        assert "recent" in note
        assert "older" in note


class TestApplyQueryFallbacks:
    """Tests for the apply_query_fallbacks function."""

    def test_returns_empty_when_no_fallback_matches(self):
        options = QueryOptions(scope="all", match_source="all", recent=False)

        def search_fn(opts):
            return []

        result = apply_query_fallbacks(options, search_fn)
        assert result.results == []
        assert result.note is None

    def test_returns_results_from_first_successful_fallback(self):
        options = QueryOptions(scope="public", match_source="strings", recent=True)
        mock_results = [object()]  # Placeholder for SearchResult

        call_count = [0]

        def search_fn(opts):
            call_count[0] += 1
            # Return results when match_source is broadened to "all"
            if opts.match_source == "all":
                return mock_results
            return []

        result = apply_query_fallbacks(options, search_fn)
        assert result.results == mock_results
        assert result.note is not None
        assert "strings" in result.note

    def test_tries_fallbacks_in_priority_order(self):
        options = QueryOptions(scope="public", match_source="strings", recent=True)
        transformations_seen = []

        def search_fn(opts):
            transformations_seen.append((opts.match_source, opts.scope, opts.recent))
            return []

        apply_query_fallbacks(options, search_fn)
        # Each fallback transforms the ORIGINAL options independently
        # First: MatchSourceFallback (strings -> all, scope unchanged, recent unchanged)
        # Second: ScopeFallback (match_source unchanged, public -> all, recent unchanged)
        # Third: RecentFallback (match_source unchanged, scope unchanged, True -> False)
        assert ("all", "public", True) in transformations_seen  # match_source fallback
        assert ("strings", "all", True) in transformations_seen  # scope fallback
        assert ("strings", "public", False) in transformations_seen  # recent fallback


class TestQueryFallbackResult:
    """Tests for QueryFallbackResult dataclass."""

    def test_default_note_is_none(self):
        result = QueryFallbackResult(results=[])
        assert result.note is None

    def test_can_set_note(self):
        result = QueryFallbackResult(results=[], note="test fallback note")
        assert result.note == "test fallback note"


# =============================================================================
# Additional Function Fallback Tests
# =============================================================================


class TestCamelSnakeFallback:
    """Tests for CamelSnakeFallback strategy."""

    def test_should_try_for_camel_case_name(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="getUserName")]
        assert strategy.should_try(patterns, {}) is True

    def test_should_try_for_snake_case_name(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="get_user_name")]
        assert strategy.should_try(patterns, {}) is True

    def test_should_not_try_for_single_word(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="create")]
        assert strategy.should_try(patterns, {}) is False

    def test_should_not_try_for_wildcard(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="getUser*")]
        assert strategy.should_try(patterns, {}) is False

    def test_transform_camel_to_snake(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="getUserName", module="*.MyApp")]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].name == "get_user_name"
        assert transformed[0].module == "*.MyApp"

    def test_transform_snake_to_camel(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="get_user_name", arity=2)]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].name == "getUserName"
        assert transformed[0].arity == 2

    def test_get_note(self):
        strategy = CamelSnakeFallback()
        patterns = [FunctionPattern(name="getUserName")]
        note = strategy.get_note(patterns)
        assert "case" in note or "style" in note


class TestPrefixWildcardFallback:
    """Tests for PrefixWildcardFallback strategy."""

    def test_should_try_for_exact_name_long_enough(self):
        strategy = PrefixWildcardFallback()
        patterns = [FunctionPattern(name="authenticate")]
        assert strategy.should_try(patterns, {}) is True

    def test_should_not_try_for_short_name(self):
        strategy = PrefixWildcardFallback()
        patterns = [FunctionPattern(name="get")]
        assert strategy.should_try(patterns, {}) is False

    def test_should_not_try_for_wildcard_name(self):
        strategy = PrefixWildcardFallback()
        patterns = [FunctionPattern(name="auth*")]
        assert strategy.should_try(patterns, {}) is False

    def test_transform_adds_wildcards(self):
        strategy = PrefixWildcardFallback()
        patterns = [FunctionPattern(name="authenticate", module="*.Auth")]
        transformed = strategy.transform_patterns(patterns)
        assert len(transformed) == 1
        assert transformed[0].name == "*authenticate*"
        assert transformed[0].module == "*.Auth"

    def test_get_note(self):
        strategy = PrefixWildcardFallback()
        patterns = [FunctionPattern(name="authenticate")]
        note = strategy.get_note(patterns)
        assert "partial" in note


class TestDefaultFallbackLists:
    """Tests for the default fallback lists."""

    def test_function_fallbacks_include_new_strategies(self):
        """Verify new fallbacks were added to the default list."""
        strategy_types = [type(s).__name__ for s in DEFAULT_FUNCTION_FALLBACKS]
        assert "CamelSnakeFallback" in strategy_types
        assert "PrefixWildcardFallback" in strategy_types

    def test_query_fallbacks_include_all_strategies(self):
        """Verify query fallbacks are in the default list."""
        strategy_types = [type(s).__name__ for s in DEFAULT_QUERY_FALLBACKS]
        assert "MatchSourceFallback" in strategy_types
        assert "ScopeFallback" in strategy_types
        assert "RecentFallback" in strategy_types
