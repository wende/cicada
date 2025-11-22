#!/usr/bin/env python
"""
Tests for Analysis Handlers - Focus on Missing Coverage

This test file specifically targets missing coverage in
cicada/mcp/handlers/analysis_handlers.py.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from mcp.types import TextContent

from cicada.mcp.handlers.analysis_handlers import AnalysisHandler


class MockIndexManager:
    """Mock index manager for testing."""

    def __init__(self, index: dict, has_keywords: bool = True):
        self._index = index
        self._has_keywords = has_keywords

    @property
    def index(self):
        return self._index

    @property
    def has_keywords(self):
        return self._has_keywords


@pytest.fixture
def mock_index_with_keywords():
    """Index with keywords for search testing."""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "line": 1,
                "moduledoc": "Test module",
                "functions": [
                    {
                        "name": "test_func",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "keywords": {"test": 1.0, "function": 0.8, "user": 0.7},
                    }
                ],
                "keywords": {"test": 1.2, "module": 0.9},
            }
        },
        "metadata": {"indexed_at": "2024-01-01"},
        "cooccurrences": {
            "test": {"user": 5, "authentication": 3},
            "authentication": {"test": 3, "validate": 2, "credentials": 4},
        },
    }


@pytest.fixture
def mock_index_without_keywords():
    """Index without keywords for error testing."""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "line": 1,
                "functions": [{"name": "test_func", "arity": 1}],
            }
        },
        "metadata": {},
    }


@pytest.fixture
def mock_index_no_cooccurrence():
    """Index without co-occurrence data."""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "keywords": {"test": 1.0},
                "functions": [],
            }
        },
        "metadata": {},
    }


# ===== suggest_keywords Tests =====


@pytest.mark.asyncio
async def test_suggest_keywords_no_cooccurrence_data(mock_index_no_cooccurrence):
    """Test suggest_keywords when co-occurrence data is missing."""
    handler = AnalysisHandler(MockIndexManager(mock_index_no_cooccurrence, has_keywords=True))

    result = await handler.suggest_keywords(
        keywords=["test"], mode="expand", top_n=5, min_cooccurrence=1
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Co-occurrence data not available" in result[0].text
    assert "cicada index --extract-keywords" in result[0].text


@pytest.mark.asyncio
async def test_suggest_keywords_expand_mode_success(mock_index_with_keywords):
    """Test suggest_keywords in expand mode with valid suggestions."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    result = await handler.suggest_keywords(
        keywords=["test"], mode="expand", top_n=5, min_cooccurrence=1
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Related keywords for: test" in result[0].text
    assert "Try searching with:" in result[0].text


@pytest.mark.asyncio
async def test_suggest_keywords_expand_mode_no_suggestions(mock_index_with_keywords):
    """Test suggest_keywords in expand mode when no suggestions found."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    # Search for keyword that doesn't exist
    result = await handler.suggest_keywords(
        keywords=["nonexistent"], mode="expand", top_n=5, min_cooccurrence=100
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No keyword suggestions found" in result[0].text
    assert "min_cooccurrence threshold is too high" in result[0].text


@pytest.mark.asyncio
async def test_suggest_keywords_narrow_mode_no_results(mock_index_with_keywords):
    """Test suggest_keywords in narrow mode without search results."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    result = await handler.suggest_keywords(
        keywords=["test"], mode="narrow", search_results=None, top_n=5
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "search_results is required for mode='narrow'" in result[0].text


@pytest.mark.asyncio
async def test_suggest_keywords_narrow_mode_success(mock_index_with_keywords):
    """Test suggest_keywords in narrow mode with valid results."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    # Mock search results
    search_results = [
        {
            "name": "TestModule",
            "type": "module",
            "keywords": {"test": 1.0, "user": 0.8},
            "extracted_keywords": {"test": 1.0, "user": 0.8},
        },
        {
            "name": "test_func",
            "type": "function",
            "keywords": {"test": 1.0, "authentication": 0.9},
            "extracted_keywords": {"test": 1.0, "authentication": 0.9},
        },
    ]

    result = await handler.suggest_keywords(
        keywords=["test"],
        mode="narrow",
        search_results=search_results,
        top_n=5,
        min_result_count=1,
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Add these keywords to narrow down" in result[0].text


@pytest.mark.asyncio
async def test_suggest_keywords_narrow_mode_no_suggestions(mock_index_with_keywords):
    """Test suggest_keywords in narrow mode when no narrowing keywords found."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    # Search results with no common keywords
    search_results = [
        {"name": "TestModule", "type": "module", "keywords": {"test": 1.0}},
    ]

    result = await handler.suggest_keywords(
        keywords=["test"],
        mode="narrow",
        search_results=search_results,
        top_n=5,
        min_result_count=100,  # Set threshold too high
    )

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No narrowing keywords found" in result[0].text
    assert "min_result_count threshold is too high" in result[0].text


# ===== query Method Tests =====


@pytest.mark.asyncio
async def test_query_without_keywords(mock_index_without_keywords):
    """Test query method when keywords are not available."""
    handler = AnalysisHandler(MockIndexManager(mock_index_without_keywords, has_keywords=False))

    result = await handler.query(query="test", scope="all", filter_type="all")

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No keywords found in index" in result[0].text
    assert "cicada index" in result[0].text


# ===== search_by_keywords Error Paths =====


@pytest.mark.asyncio
async def test_search_by_keywords_no_keywords_in_index(mock_index_without_keywords):
    """Test search_by_keywords when index has no keywords."""
    handler = AnalysisHandler(MockIndexManager(mock_index_without_keywords, has_keywords=False))

    result = await handler.search_by_keywords(keywords=["test"])

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No keywords found in index" in result[0].text
    assert "cicada index --force --regular" in result[0].text


@pytest.mark.asyncio
async def test_search_by_keywords_no_results_with_min_score(mock_index_with_keywords):
    """Test search_by_keywords when no results meet min_score threshold."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    # Use a very high min_score that no results will meet
    result = await handler.search_by_keywords(keywords=["nonexistent"], min_score=10.0)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No results found for keywords: nonexistent" in result[0].text
    assert "min_score >= 10.0" in result[0].text


@pytest.mark.asyncio
async def test_search_by_keywords_no_results_without_min_score(
    mock_index_with_keywords,
):
    """Test search_by_keywords when no results found (no min_score)."""
    handler = AnalysisHandler(MockIndexManager(mock_index_with_keywords, has_keywords=True))

    result = await handler.search_by_keywords(keywords=["nonexistent_keyword_12345"], min_score=0.0)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "No results found for keywords:" in result[0].text
    # Should NOT mention min_score when it's 0.0
    assert "min_score" not in result[0].text


# ===== query_jq Timeout and Error Tests =====


@pytest.mark.asyncio
async def test_query_jq_timeout():
    """Test query_jq when jq execution times out."""
    handler = AnalysisHandler(MockIndexManager({"modules": {}}, has_keywords=False))

    with patch.object(handler, "_execute_jq_query", side_effect=asyncio.TimeoutError()):
        result = await handler.query_jq(query=".modules", output_format="json")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "jq query timed out" in result[0].text
        assert "30 seconds" in result[0].text
        assert "simplifying your query" in result[0].text


@pytest.mark.asyncio
async def test_query_jq_value_error_syntax():
    """Test query_jq when jq has syntax error with line/column info."""
    handler = AnalysisHandler(MockIndexManager({"modules": {}}, has_keywords=False))

    # Simulate jq syntax error with line and column information
    error_msg = "jq: error (at <stdin>:0): compile error near line 1, column 5: Invalid syntax"

    with patch.object(handler, "_execute_jq_query", side_effect=ValueError(error_msg)):
        result = await handler.query_jq(query=".bad[", output_format="json")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "syntax error at line 1, column 5" in result[0].text
        assert "Common issues:" in result[0].text


@pytest.mark.asyncio
async def test_query_jq_value_error_iterate_null():
    """Test query_jq with 'iterate over null' error."""
    handler = AnalysisHandler(MockIndexManager({"modules": {}}, has_keywords=False))

    error_msg = "Cannot iterate over null"

    with patch.object(handler, "_execute_jq_query", side_effect=ValueError(error_msg)):
        result = await handler.query_jq(query=".functions[]", output_format="json")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "iterate" in result[0].text.lower()
        assert "null" in result[0].text.lower()
        assert "HINT" in result[0].text
        assert ".functions[]?" in result[0].text


@pytest.mark.asyncio
async def test_query_jq_general_exception():
    """Test query_jq when unexpected exception occurs."""
    handler = AnalysisHandler(MockIndexManager({"modules": {}}, has_keywords=False))

    with patch.object(handler, "_execute_jq_query", side_effect=RuntimeError("Unexpected error")):
        result = await handler.query_jq(query=".modules", output_format="json")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unexpected error executing jq query" in result[0].text
        assert "Unexpected error" in result[0].text


@pytest.mark.asyncio
async def test_query_jq_null_result():
    """Test query_jq when result is None/null."""
    handler = AnalysisHandler(MockIndexManager({"modules": {}}, has_keywords=False))

    with patch.object(handler, "_execute_jq_query", return_value=None):
        result = await handler.query_jq(query=".nonexistent", output_format="json")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Query returned null" in result[0].text
        assert "field doesn't exist" in result[0].text
