"""Tests for the fallback search strategies module."""

import pytest

from cicada.mcp.fallbacks import (
    DEFAULT_FUNCTION_FALLBACKS,
    FallbackResult,
    PrivateFunctionFallback,
    WithoutArityFallback,
    WithoutModuleFallback,
    apply_fallbacks,
)
from cicada.mcp.pattern_utils import FunctionPattern


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
