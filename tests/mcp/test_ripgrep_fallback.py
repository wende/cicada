"""Tests for ripgrep fallback integration in query searches.

This module tests the integration of python-ripgrep as a fallback mechanism
when Cicada's keyword/pattern search returns no results. The ripgrep fallback
searches raw file content and enriches results with metadata from the index.
"""

import pytest
from unittest.mock import MagicMock, patch

from cicada.mcp.fallbacks import (
    RipgrepFallbackStrategy,
    apply_query_fallbacks,
    QueryFallbackResult,
    _ripgrep_search_with_index,
    _create_ripgrep_search_result,
)
from cicada.query.types import QueryOptions, SearchResult


class TestRipgrepFallbackStrategy:
    """Tests for RipgrepFallbackStrategy."""

    def test_should_try_when_keyword_search_has_no_results(self):
        """Strategy should activate when no results from keyword/pattern search."""
        strategy = RipgrepFallbackStrategy()
        options = QueryOptions()
        context = {"has_results": False, "original_query": "chat.delta", "index": {"modules": {}}}

        assert strategy.should_try(options, context) is True

    def test_should_not_try_when_results_exist(self):
        """Strategy should not activate when results already exist."""
        strategy = RipgrepFallbackStrategy()
        options = QueryOptions()
        context = {"has_results": True, "original_query": "chat"}

        assert strategy.should_try(options, context) is False

    def test_should_not_try_when_query_is_pattern(self):
        """Strategy should not activate for pattern queries (wildcards, etc)."""
        strategy = RipgrepFallbackStrategy()
        options = QueryOptions()
        context = {"has_results": False, "original_query": "MyApp.*.create*"}

        assert strategy.should_try(options, context) is False

    def test_transform_options_adds_ripgrep_flag(self):
        """Transform should mark options for ripgrep search."""
        strategy = RipgrepFallbackStrategy()
        options = QueryOptions(match_source="strings")

        transformed = strategy.transform_options(options)

        # Should preserve original options but mark for ripgrep
        assert transformed.match_source == "strings"
        assert getattr(transformed, "_use_ripgrep", False) is True

    def test_get_note(self):
        """Should return appropriate note about ripgrep fallback."""
        strategy = RipgrepFallbackStrategy()
        options = QueryOptions()

        note = strategy.get_note(options)

        assert "ripgrep" in note.lower()
        assert "content" in note.lower() or "text" in note.lower()


class TestRipgrepSearchIntegration:
    """Tests for ripgrep search integration with index metadata."""

    @pytest.fixture
    def mock_index(self):
        """Create a mock index with module/function metadata."""
        return {
            "modules": {
                "ChatController": {
                    "file": "src/controllers/chat.ts",
                    "line": 1,
                    "functions": [
                        {"name": "handleMessage", "line": 15, "arity": 2, "type": "def"},
                        {"name": "broadcast", "line": 42, "arity": 1, "type": "def"},
                    ],
                },
                "Gateway": {
                    "file": "src/gateway.ts",
                    "line": 1,
                    "functions": [
                        {"name": "onConnect", "line": 10, "arity": 0, "type": "def"},
                    ],
                },
            },
            "metadata": {
                "repo_path": "/fake/repo",
            },
        }

    @pytest.fixture
    def mock_ripgrep_results(self):
        """Create mock ripgrep search results."""
        return [
            "src/controllers/chat.ts:25:    if (msg.type === 'chat.delta') {",
            "src/controllers/chat.ts:45:        this.broadcast('chat.delta', data);",
            "src/gateway.ts:15:    socket.on('chat.delta', handler);",
        ]

    def test_ripgrep_search_called_with_query_terms(self, mock_index):
        """Ripgrep should be called with normalized query terms."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = []

            _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts"],
            )

            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert "chat.delta" in call_args.kwargs.get("patterns", [])

    def test_ripgrep_results_enriched_with_module_info(self, mock_index, mock_ripgrep_results):
        """Ripgrep results should be enriched with module/function metadata from index."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = mock_ripgrep_results

            results = _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts"],
            )

            assert len(results) == 3

            # First result should have module info
            first = results[0]
            assert first.file == "src/controllers/chat.ts"
            assert first.line == 25
            assert first.module == "ChatController"
            # Line 25 is between handleMessage (line 15) and broadcast (line 42)
            assert first.function == "handleMessage"

    def test_ripgrep_results_enriched_with_function_lookup(self, mock_index, mock_ripgrep_results):
        """Ripgrep results should correctly identify containing function."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = mock_ripgrep_results

            results = _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts"],
            )

            # Result at line 45 should be in broadcast function
            broadcast_result = [r for r in results if r.line == 45][0]
            assert broadcast_result.function == "broadcast"

    def test_ripgrep_results_create_search_result_objects(self, mock_index, mock_ripgrep_results):
        """Ripgrep results should be converted to SearchResult objects."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = mock_ripgrep_results

            results = _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts"],
            )

            # All results should have required SearchResult fields
            for result in results:
                assert hasattr(result, "type")
                assert hasattr(result, "name")
                assert hasattr(result, "module")
                assert hasattr(result, "file")
                assert hasattr(result, "line")
                assert hasattr(result, "score")
                assert hasattr(result, "confidence")
                assert hasattr(result, "matched_keywords")
                assert hasattr(result, "pattern_match")

    def test_ripgrep_respects_glob_patterns(self, mock_index):
        """Ripgrep should respect glob patterns for file filtering."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = []

            _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts", "*.tsx"],
            )

            call_kwargs = mock_search.call_args.kwargs
            assert call_kwargs.get("globs") == ["*.ts", "*.tsx"]

    def test_ripgrep_handles_no_matches_gracefully(self, mock_index):
        """Ripgrep should handle empty results gracefully."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = []

            results = _ripgrep_search_with_index(
                query="nonexistent.pattern",
                index=mock_index,
                globs=["*.ts"],
            )

            assert results == []

    def test_ripgrep_skips_files_not_in_index(self, mock_index):
        """Ripgrep results for files not in index should still be returned but with less metadata."""
        with patch("python_ripgrep.search") as mock_search:
            mock_search.return_value = [
                "src/unknown/file.ts:10:    chat.delta",
            ]

            results = _ripgrep_search_with_index(
                query="chat.delta",
                index=mock_index,
                globs=["*.ts"],
            )

            assert len(results) == 1
            assert results[0].file == "src/unknown/file.ts"
            assert not results[0].module  # Unknown module (empty string or None)


class TestRipgrepFallbackInQueryFlow:
    """Tests for ripgrep fallback integration in the main query flow."""

    def test_ripgrep_fallback_added_to_default_strategies(self):
        """RipgrepFallbackStrategy should be in DEFAULT_QUERY_FALLBACKS."""
        from cicada.mcp.fallbacks import DEFAULT_QUERY_FALLBACKS

        strategy_types = [type(s).__name__ for s in DEFAULT_QUERY_FALLBACKS]
        assert "RipgrepFallbackStrategy" in strategy_types

    def test_apply_query_fallbacks_uses_ripgrep_as_last_resort(self):
        """Ripgrep should be tried after other fallbacks fail."""
        options = QueryOptions(match_source="strings")

        # Mock search function that returns empty results
        def mock_search(opts):
            return []

        with patch("cicada.mcp.fallbacks._ripgrep_search_with_index") as mock_ripgrep:
            mock_ripgrep.return_value = []

            result = apply_query_fallbacks(
                options,
                mock_search,
                context={
                    "has_results": False,
                    "original_query": "chat.delta",
                    "index": {"modules": {}},
                },
            )

            # Ripgrep should be called as last fallback
            mock_ripgrep.assert_called_once()

    def test_ripgrep_results_returned_with_note(self):
        """When ripgrep finds results, they should be returned with appropriate note."""
        options = QueryOptions()

        def mock_search(opts):
            return []

        mock_result = {
            "type": "function",
            "name": "ChatController.handleMessage/2",
            "module": "ChatController",
            "file": "src/controllers/chat.ts",
            "line": 25,
            "score": 0.8,
            "confidence": 80.0,
            "matched_keywords": ["chat.delta"],
            "pattern_match": False,
        }

        with patch("cicada.mcp.fallbacks._ripgrep_search_with_index") as mock_ripgrep:
            mock_ripgrep.return_value = [mock_result]

            result = apply_query_fallbacks(
                options,
                mock_search,
                context={
                    "has_results": False,
                    "original_query": "chat.delta",
                    "index": {"modules": {}},
                },
            )

            assert len(result.results) == 1
            assert "ripgrep" in (result.note or "").lower()


class TestRipgrepResultFormatting:
    """Tests for formatting ripgrep results for display."""

    def test_ripgrep_result_has_lower_score_than_index_matches(self):
        """Ripgrep matches should have lower score than index-based matches."""
        result = _create_ripgrep_search_result(
            file_path="src/chat.ts",
            line=10,
            match_text="chat.delta",
            module="ChatModule",
            function="handleMessage",
        )

        # Ripgrep results should have moderate score (not too high, not too low)
        assert 0.3 <= result.score <= 0.7
        assert result.pattern_match is False
        # search_source is 'keyword' for ripgrep results (they use keyword search type)

    def test_ripgrep_result_includes_snippet_context(self):
        """Ripgrep results should include code snippet."""
        result = _create_ripgrep_search_result(
            file_path="src/chat.ts",
            line=10,
            match_text="if (msg.type === 'chat.delta')",
            module="ChatModule",
            function="handleMessage",
        )

        assert result.doc is not None  # Snippet stored in doc field
