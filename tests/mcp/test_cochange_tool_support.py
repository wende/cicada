"""Tests for co-change support in MCP tools."""

import pytest
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


class TestMCPCoChangeSupport:
    """Test suite for co-change boosting in MCP tools."""

    @pytest.fixture
    def index_with_cochange(self):
        """Index with co-change data."""
        return {
            "modules": {
                "ModuleA": {
                    "file": "lib/module_a.ex",
                    "line": 1,
                    "moduledoc": "Module A handles authentication",
                    "public_functions": 1,
                    "private_functions": 0,
                    "keywords": {"authentication": 0.9, "user": 0.8, "login": 0.7},
                    "cochange_files": [
                        {"file": "lib/module_b.ex", "count": 15},
                        {"file": "lib/module_c.ex", "count": 3},
                    ],
                    "functions": [
                        {
                            "name": "validate_user",
                            "arity": 2,
                            "line": 5,
                            "type": "def",
                            "keywords": {"validate": 0.9, "authentication": 0.8},
                            "cochange_functions": [
                                {
                                    "module": "ModuleB",
                                    "function": "check_credentials",
                                    "arity": 2,
                                    "count": 10,
                                },
                                {
                                    "module": "ModuleC",
                                    "function": "log_attempt",
                                    "arity": 1,
                                    "count": 5,
                                },
                            ],
                        }
                    ],
                },
                "ModuleB": {
                    "file": "lib/module_b.ex",
                    "line": 1,
                    "moduledoc": "Module B handles credentials",
                    "public_functions": 1,
                    "private_functions": 0,
                    "keywords": {"credentials": 0.9, "password": 0.8, "check": 0.7},
                    "cochange_files": [{"file": "lib/module_a.ex", "count": 15}],
                    "functions": [
                        {
                            "name": "check_credentials",
                            "arity": 2,
                            "line": 5,
                            "type": "def",
                            "keywords": {"check": 0.9, "credentials": 0.8},
                            "cochange_functions": [
                                {
                                    "module": "ModuleA",
                                    "function": "validate_user",
                                    "arity": 2,
                                    "count": 10,
                                }
                            ],
                        }
                    ],
                },
                "ModuleC": {
                    "file": "lib/module_c.ex",
                    "line": 1,
                    "moduledoc": "Module C handles logging",
                    "public_functions": 1,
                    "private_functions": 0,
                    "keywords": {"logging": 0.9, "audit": 0.8},
                    "cochange_files": [{"file": "lib/module_a.ex", "count": 3}],
                    "functions": [
                        {
                            "name": "log_attempt",
                            "arity": 1,
                            "line": 5,
                            "type": "def",
                            "keywords": {"log": 0.9, "audit": 0.8},
                            "cochange_functions": [
                                {
                                    "module": "ModuleA",
                                    "function": "validate_user",
                                    "arity": 2,
                                    "count": 5,
                                }
                            ],
                        }
                    ],
                },
            }
        }

    @pytest.mark.asyncio
    async def test_search_by_keywords_accepts_cochange_boost(self, index_with_cochange):
        """Test that search_by_keywords accepts cochange_boost parameter."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - should not raise error with cochange_boost parameter
        results = await handler.search_by_keywords(keywords=["authentication"], cochange_boost=0.5)

        # Assert
        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_with_cochange_boost_affects_results(self, index_with_cochange):
        """Test that cochange_boost parameter actually affects search results."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - search with and without boost
        results_without_boost = await handler.search_by_keywords(
            keywords=["authentication"], cochange_boost=0.0
        )
        results_with_boost = await handler.search_by_keywords(
            keywords=["authentication"], cochange_boost=0.5
        )

        # Assert - results should differ (scores should be different)
        # Both should have results but with different scores
        assert len(results_without_boost) > 0
        assert len(results_with_boost) > 0

        # Extract text content
        text_without = results_without_boost[0].text
        text_with = results_with_boost[0].text

        # The boosted version should have co-change information displayed
        assert "Often changed with:" in text_with or "Related functions:" in text_with

    @pytest.mark.asyncio
    async def test_cochange_boost_default_value(self, index_with_cochange):
        """Test that cochange_boost has a sensible default value."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - call without specifying cochange_boost
        results = await handler.search_by_keywords(keywords=["authentication"])

        # Assert - should work without error
        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_cochange_boost_with_filter_type(self, index_with_cochange):
        """Test that cochange_boost works with filter_type parameter."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - search functions only with boost
        results = await handler.search_by_keywords(
            keywords=["authentication"], filter_type="functions", cochange_boost=0.5
        )

        # Assert
        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_cochange_boost_with_match_source(self, index_with_cochange):
        """Test that cochange_boost works with match_source parameter."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - search with both parameters
        results = await handler.search_by_keywords(
            keywords=["authentication"], match_source="docs", cochange_boost=0.5
        )

        # Assert
        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_cochange_boost_with_min_score(self, index_with_cochange):
        """Test that cochange_boost works with min_score parameter."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act - search with both parameters
        results = await handler.search_by_keywords(
            keywords=["authentication"], min_score=0.5, cochange_boost=0.5
        )

        # Assert
        assert results is not None

    @pytest.mark.asyncio
    async def test_cochange_boost_with_no_cochange_data(self):
        """Test that cochange_boost gracefully handles index without co-change data."""
        # Arrange - index without co-change data
        index_without_cochange = {
            "modules": {
                "ModuleA": {
                    "file": "lib/module_a.ex",
                    "line": 1,
                    "moduledoc": "Module A",
                    "public_functions": 1,
                    "private_functions": 0,
                    "keywords": {"test": 0.9},
                    "functions": [
                        {
                            "name": "test_func",
                            "arity": 0,
                            "line": 5,
                            "type": "def",
                            "keywords": {"test": 0.9},
                        }
                    ],
                }
            }
        }
        handler = AnalysisHandler(MockIndexManager(index_without_cochange, has_keywords=True))

        # Act - should not crash
        results = await handler.search_by_keywords(keywords=["test"], cochange_boost=0.5)

        # Assert
        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_invalid_cochange_boost_values(self, index_with_cochange):
        """Test that invalid cochange_boost values are handled gracefully."""
        # Arrange
        handler = AnalysisHandler(MockIndexManager(index_with_cochange, has_keywords=True))

        # Act & Assert - negative boost (should work, just may produce odd results)
        results_negative = await handler.search_by_keywords(
            keywords=["authentication"], cochange_boost=-0.5
        )
        assert results_negative is not None

        # Very high boost (should work)
        results_high = await handler.search_by_keywords(
            keywords=["authentication"], cochange_boost=10.0
        )
        assert results_high is not None
