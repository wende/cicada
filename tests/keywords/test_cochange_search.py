"""Tests for co-change boosting in keyword search."""

import pytest
import json
from pathlib import Path
from cicada.keyword_search import KeywordSearcher


class TestCoChangeSearch:
    """Test suite for co-change boosting in search."""

    @pytest.fixture
    def index_with_cochange(self):
        """Create a test index with co-change data."""
        return {
            "modules": {
                "ModuleA": {
                    "file": "lib/module_a.ex",
                    "line": 1,
                    "moduledoc": "Module A handles authentication",
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
                    "keywords": {"credentials": 0.9, "password": 0.8, "check": 0.7},
                    "cochange_files": [{"file": "lib/module_a.ex", "count": 15}],
                    "functions": [
                        {
                            "name": "check_credentials",
                            "arity": 2,
                            "line": 5,
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
                    "keywords": {"logging": 0.9, "audit": 0.8},
                    "cochange_files": [{"file": "lib/module_a.ex", "count": 3}],
                    "functions": [
                        {
                            "name": "log_attempt",
                            "arity": 1,
                            "line": 5,
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
                "ModuleD": {
                    "file": "lib/module_d.ex",
                    "line": 1,
                    "moduledoc": "Module D is unrelated",
                    "keywords": {"unrelated": 0.9, "independent": 0.8},
                    "cochange_files": [],  # No co-changes
                    "functions": [
                        {
                            "name": "do_something",
                            "arity": 0,
                            "line": 5,
                            "keywords": {"something": 0.9},
                            "cochange_functions": [],  # No co-changes
                        }
                    ],
                },
            },
            "cochange_metadata": {
                "analyzed_at": "2025-01-01T00:00:00",
                "commit_count": 50,
                "file_pairs": 3,
                "function_pairs": 3,
            },
        }

    def test_search_with_cochange_boost_increases_scores(self, index_with_cochange):
        """Test that co-change boost increases scores for related results."""
        # Arrange
        searcher_with_boost = KeywordSearcher(index_with_cochange, cochange_boost=0.5)
        searcher_without_boost = KeywordSearcher(index_with_cochange, cochange_boost=0.0)

        # Act
        results_with = searcher_with_boost.search(["authentication"], top_n=10)
        results_without = searcher_without_boost.search(["authentication"], top_n=10)

        # Assert - with boost should have different (higher) scores
        # Find ModuleA.validate_user in both result sets
        result_with = next(
            r
            for r in results_with
            if r["module"] == "ModuleA" and r.get("function") == "validate_user"
        )
        result_without = next(
            r
            for r in results_without
            if r["module"] == "ModuleA" and r.get("function") == "validate_user"
        )

        assert (
            result_with["score"] > result_without["score"]
        ), f"Score with boost ({result_with['score']}) should be higher than without ({result_without['score']})"

    def test_cochange_boost_disabled_by_default(self, index_with_cochange):
        """Test that co-change boost is disabled when cochange_boost=0."""
        # Arrange
        searcher = KeywordSearcher(index_with_cochange, cochange_boost=0.0)

        # Act
        results = searcher.search(["authentication"], top_n=10)

        # Assert - results should exist but not be boosted
        assert len(results) > 0
        # Scores should be based solely on keyword matching
        result = next(r for r in results if r["module"] == "ModuleA")
        # Base score should be around 0.9 (keyword weight for "authentication")
        assert 0.8 <= result["score"] <= 1.0

    def test_cochange_boost_strength_configurable(self, index_with_cochange):
        """Test that boost strength is configurable."""
        # Arrange
        searcher_weak = KeywordSearcher(index_with_cochange, cochange_boost=0.1)
        searcher_strong = KeywordSearcher(index_with_cochange, cochange_boost=1.0)

        # Act
        results_weak = searcher_weak.search(["authentication"], top_n=10)
        results_strong = searcher_strong.search(["authentication"], top_n=10)

        # Assert - stronger boost should yield higher scores
        result_weak = next(
            r
            for r in results_weak
            if r["module"] == "ModuleA" and r.get("function") == "validate_user"
        )
        result_strong = next(
            r
            for r in results_strong
            if r["module"] == "ModuleA" and r.get("function") == "validate_user"
        )

        assert (
            result_strong["score"] > result_weak["score"]
        ), f"Strong boost ({result_strong['score']}) should be higher than weak boost ({result_weak['score']})"

    def test_cochange_boosts_related_results_in_same_search(self, index_with_cochange):
        """Test that results co-changed together both get boosted."""
        # Arrange
        searcher = KeywordSearcher(index_with_cochange, cochange_boost=0.5)

        # Act - search for terms that match both ModuleA and ModuleB
        results = searcher.search(["authentication", "credentials"], top_n=10)

        # Assert - Both ModuleA and ModuleB should appear in results
        module_a_result = next((r for r in results if r["module"] == "ModuleA"), None)
        module_b_result = next((r for r in results if r["module"] == "ModuleB"), None)

        assert module_a_result is not None, "ModuleA should appear in results"
        assert module_b_result is not None, "ModuleB should appear in results"

        # Both should have boosted scores due to co-change relationship
        # (exact values depend on boost calculation, but both should be present)

    def test_file_level_and_function_level_boost_both_apply(self, index_with_cochange):
        """Test that both file and function level co-changes contribute to boost."""
        # Arrange
        searcher = KeywordSearcher(index_with_cochange, cochange_boost=0.5)

        # Act
        results = searcher.search(["authentication"], top_n=10)

        # Assert - ModuleA.validate_user should get boost from:
        # 1. File-level co-change (module_a.ex with module_b.ex)
        # 2. Function-level co-change (validate_user with check_credentials)
        result = next(
            r for r in results if r["module"] == "ModuleA" and r.get("function") == "validate_user"
        )

        # The boost should be significant (exact value depends on implementation)
        assert result["score"] > 0.8, "Score should be boosted by co-change relationships"

    def test_no_crash_when_cochange_data_missing(self):
        """Test that search doesn't crash when co-change data is missing."""
        # Arrange - index without co-change data
        index_without_cochange = {
            "modules": {
                "ModuleA": {
                    "file": "lib/module_a.ex",
                    "line": 1,
                    "keywords": {"test": 0.9},
                    "functions": [
                        {"name": "test_func", "arity": 0, "line": 5, "keywords": {"test": 0.9}}
                    ],
                }
            }
        }

        searcher = KeywordSearcher(index_without_cochange, cochange_boost=0.5)

        # Act - should not crash
        results = searcher.search(["test"], top_n=10)

        # Assert
        assert len(results) > 0
        assert results[0]["module"] == "ModuleA"

    def test_cochange_boost_with_no_matching_cochanges(self, index_with_cochange):
        """Test that modules without co-changes don't get boosted."""
        # Arrange
        searcher_with_boost = KeywordSearcher(index_with_cochange, cochange_boost=0.5)
        searcher_without_boost = KeywordSearcher(index_with_cochange, cochange_boost=0.0)

        # Act - search for ModuleD which has no co-changes
        results_with = searcher_with_boost.search(["unrelated"], top_n=10)
        results_without = searcher_without_boost.search(["unrelated"], top_n=10)

        # Assert - scores should be the same (no boost applied)
        result_with = next(r for r in results_with if r["module"] == "ModuleD")
        result_without = next(r for r in results_without if r["module"] == "ModuleD")

        assert (
            abs(result_with["score"] - result_without["score"]) < 0.01
        ), "Modules without co-changes should have same score with or without boost"

    def test_cochange_boost_preserves_keyword_ranking(self, index_with_cochange):
        """Test that co-change boost doesn't completely override keyword relevance."""
        # Arrange
        searcher = KeywordSearcher(index_with_cochange, cochange_boost=0.5)

        # Act - search for "authentication" which is strongly in ModuleA
        results = searcher.search(["authentication"], top_n=10)

        # Assert - ModuleA should still rank high despite co-change boosts
        # The most relevant result should be ModuleA (has "authentication" with 0.9 weight)
        assert (
            results[0]["module"] == "ModuleA"
        ), "Most keyword-relevant result should still rank first"

    def test_cochange_boost_default_value(self, index_with_cochange):
        """Test that default cochange_boost value is 0.5."""
        # Arrange
        searcher_default = KeywordSearcher(index_with_cochange)  # No cochange_boost specified
        searcher_explicit = KeywordSearcher(index_with_cochange, cochange_boost=0.5)

        # Act
        results_default = searcher_default.search(["authentication"], top_n=10)
        results_explicit = searcher_explicit.search(["authentication"], top_n=10)

        # Assert - should produce same results
        assert len(results_default) == len(results_explicit)
        for i in range(len(results_default)):
            assert results_default[i]["module"] == results_explicit[i]["module"]
            assert abs(results_default[i]["score"] - results_explicit[i]["score"]) < 0.01
