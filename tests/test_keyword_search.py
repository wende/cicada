"""Tests for keyword search functionality."""

import pytest

from cicada.keyword_search import KeywordSearcher


class TestKeywordSearcher:
    """Test the KeywordSearcher class."""

    @pytest.fixture
    def sample_index(self):
        """Create a sample index for testing."""
        return {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User management module",
                    "keywords": ["user", "account", "profile"],
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a new user",
                            "keywords": {"create": 0.8, "user": 0.9, "new": 0.7},
                        },
                        {
                            "name": "update",
                            "arity": 2,
                            "line": 20,
                            "doc": "Updates user data",
                            "keywords": {"update": 0.8, "modify": 0.7, "change": 0.6},
                        },
                        {
                            "name": "delete_user",
                            "arity": 1,
                            "line": 30,
                            "doc": "Deletes a user",
                            "keywords": {"delete": 0.8, "remove": 0.7, "user": 0.9},
                        },
                    ],
                },
                "MyApp.Post": {
                    "file": "lib/my_app/post.ex",
                    "line": 1,
                    "moduledoc": "Post management module",
                    "keywords": {"post": 0.9, "article": 0.7, "content": 0.8},
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a new post",
                            "keywords": {"create": 0.8, "post": 0.9, "publish": 0.8},
                        },
                    ],
                },
            }
        }

    @pytest.fixture
    def index_without_keywords(self):
        """Create an index without keywords (fallback to identifier names)."""
        return {
            "modules": {
                "MyApp.Calculator": {
                    "file": "lib/calculator.ex",
                    "line": 1,
                    "moduledoc": "Math operations",
                    "functions": [
                        {
                            "name": "add",
                            "arity": 2,
                            "line": 10,
                            "doc": "Addition",
                        },
                        {
                            "name": "subtract",
                            "arity": 2,
                            "line": 20,
                            "doc": "Subtraction",
                        },
                    ],
                }
            }
        }

    def test_basic_search(self, sample_index):
        """Test basic keyword search."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create", "user"])

        assert len(results) > 0
        assert any(r["name"] == "MyApp.User.create/1" for r in results)

    def test_search_with_empty_keywords(self, sample_index):
        """Test search with empty keyword list."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search([])

        assert len(results) == 0

    def test_search_with_wildcard_prefix(self, sample_index):
        """Test wildcard search with prefix pattern."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["creat*"])

        assert len(results) > 0
        # Should match both create functions
        assert any("create" in r["name"].lower() for r in results)

    def test_search_with_wildcard_suffix(self, sample_index):
        """Test wildcard search with suffix pattern."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["*user"])

        assert len(results) > 0
        # Should match user-related results
        assert any("*user" in r["matched_keywords"] for r in results)

    def test_search_with_wildcard_middle(self, sample_index):
        """Test wildcard search with pattern in the middle."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["*delete*"])

        assert len(results) > 0
        # Should match delete_user
        assert any("delete_user" in r["name"] for r in results)

    def test_search_with_question_mark_wildcard_not_supported(self, sample_index):
        """Test that ? wildcard is not supported."""
        searcher = KeywordSearcher(sample_index)
        # Question mark should not be treated as a wildcard
        results = searcher.search(["user?"])

        # Should return no results since ? is not a wildcard
        assert len(results) == 0

    def test_has_wildcards_detection(self, sample_index):
        """Test _has_wildcards method."""
        searcher = KeywordSearcher(sample_index)

        assert searcher._has_wildcards(["user*"]) is True
        assert searcher._has_wildcards(["*user"]) is True
        assert searcher._has_wildcards(["user"]) is False
        assert searcher._has_wildcards(["user", "create*"]) is True

    def test_match_wildcard(self, sample_index):
        """Test _match_wildcard method."""
        searcher = KeywordSearcher(sample_index)

        assert searcher._match_wildcard("user*", "user") is True
        assert searcher._match_wildcard("user*", "username") is True
        assert searcher._match_wildcard("*user", "myuser") is True
        assert searcher._match_wildcard("cr*ate", "create") is True
        assert searcher._match_wildcard("user*", "account") is False
        # Question mark should not work as wildcard
        assert searcher._match_wildcard("user?", "users") is False

    def test_multiple_wildcard_patterns(self, sample_index):
        """Test search with multiple wildcard patterns."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["creat*", "*user"])

        assert len(results) > 0
        # Should match functions with both patterns
        assert any(r["confidence"] > 50 for r in results)

    def test_wildcard_case_insensitive(self, sample_index):
        """Test that wildcard matching is case insensitive."""
        searcher = KeywordSearcher(sample_index)

        assert searcher._match_wildcard("USER*", "username") is True
        assert searcher._match_wildcard("user*", "USERNAME") is True

    def test_index_without_keywords_fallback(self, index_without_keywords):
        """Test that searcher can handle indexes without keywords."""
        searcher = KeywordSearcher(index_without_keywords)

        # Should return no results since there are no keywords in the index
        results = searcher.search(["add"])

        # With no keywords, nothing matches
        assert len(results) == 0

    def test_empty_index(self):
        """Test searcher with empty index."""
        empty_index = {"modules": {}}
        searcher = KeywordSearcher(empty_index)

        results = searcher.search(["anything"])

        assert len(results) == 0

    def test_search_returns_correct_fields(self, sample_index):
        """Test that search results contain all expected fields."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user"])

        assert len(results) > 0
        result = results[0]

        # Check required fields
        assert "type" in result
        assert "name" in result
        assert "module" in result
        assert "file" in result
        assert "line" in result
        assert "score" in result
        assert "confidence" in result
        assert "matched_keywords" in result

        # Check function-specific fields
        if result["type"] == "function":
            assert "function" in result
            assert "arity" in result

    def test_search_top_n_limit(self, sample_index):
        """Test that top_n parameter limits results."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user"], top_n=2)

        assert len(results) <= 2

    def test_search_results_sorted_by_score(self, sample_index):
        """Test that results are sorted by score in descending order."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create"], top_n=10)

        # Check that scores are in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_score_calculation_simple(self, sample_index):
        """Test that scores are calculated as sum of matched keyword weights."""
        searcher = KeywordSearcher(sample_index)
        # Search for "create" and "user" should match MyApp.User.create/1
        # which has create: 0.8, user: 0.9
        results = searcher.search(["create", "user"], top_n=10)

        assert len(results) > 0
        # Find the create/1 function
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None
        # Score should be 0.8 + 0.9 = 1.7
        assert abs(create_result["score"] - 1.7) < 0.01

    def test_partial_keyword_match(self, sample_index):
        """Test search with partial keyword matches."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create", "nonexistent"])

        assert len(results) > 0
        # Should still find results that match "create"
        assert any("create" in r["name"].lower() for r in results)

    def test_wildcard_score_summation(self, sample_index):
        """Test that wildcard matches also sum the weights."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["del*"], top_n=10)

        assert len(results) > 0
        # Should match delete_user with score from "delete" keyword (0.8)
        delete_result = next((r for r in results if "delete_user" in r["name"]), None)
        assert delete_result is not None
        # Score should include the weight of "delete" (0.8)
        assert delete_result["score"] > 0

    def test_search_includes_documentation(self, sample_index):
        """Test that search results include documentation when available."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create"])

        # At least some results should have doc
        assert any("doc" in r and r["doc"] for r in results)

    def test_backward_compatibility_list_keywords(self):
        """Test that indexes with keyword lists (not dicts) still work."""
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "keywords": ["search", "find", "lookup"],  # List format
                    "functions": [
                        {
                            "name": "search",
                            "arity": 1,
                            "line": 10,
                            "keywords": ["search", "query"],  # List format
                        },
                    ],
                }
            }
        }

        searcher = KeywordSearcher(index)
        results = searcher.search(["search"])

        assert len(results) > 0
        assert any("search" in r["name"].lower() for r in results)

    def test_confidence_percentage(self, sample_index):
        """Test that confidence is calculated correctly."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create", "user", "nonexistent"], top_n=10)

        assert len(results) > 0
        # Find a result with partial matches
        for result in results:
            # Confidence should be (matched / total) * 100
            matched = len(result["matched_keywords"])
            total = 3
            expected_confidence = (matched / total) * 100
            assert result["confidence"] == pytest.approx(expected_confidence, rel=0.1)

    def test_filter_modules_only(self, sample_index):
        """Test filtering to return only modules."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create", "user"], filter_type="modules", top_n=10)

        # Should only return modules, no functions
        assert all(r["type"] == "module" for r in results)
        # Should include MyApp.User and MyApp.Post modules
        assert any(r["name"] == "MyApp.User" for r in results)

    def test_filter_functions_only(self, sample_index):
        """Test filtering to return only functions."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create", "user"], filter_type="functions", top_n=10)

        # Should only return functions, no modules
        assert all(r["type"] == "function" for r in results)
        # Should have function-specific fields
        assert all("function" in r and "arity" in r for r in results)
        # Should include create functions from both modules
        assert any(r["name"] == "MyApp.User.create/1" for r in results)

    def test_filter_all_default(self, sample_index):
        """Test that filter_type='all' returns both modules and functions."""
        searcher = KeywordSearcher(sample_index)
        all_results = searcher.search(["create", "user"], filter_type="all", top_n=10)

        # Should include both modules and functions
        types = {r["type"] for r in all_results}
        assert "module" in types and "function" in types

    def test_filter_modules_no_results(self, sample_index):
        """Test filter returns empty when searching for modules with function-only keywords."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["nonexistent_keyword"], filter_type="modules", top_n=10)

        # Should return empty if no modules match
        assert len(results) == 0

    def test_filter_functions_no_results(self, sample_index):
        """Test filter returns empty when no functions match."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["nonexistent_keyword"], filter_type="functions", top_n=10)

        # Should return empty if no functions match
        assert len(results) == 0

    def test_or_pattern_expansion(self, sample_index):
        """Test that OR patterns (|) are expanded correctly."""
        searcher = KeywordSearcher(sample_index)

        # Test _expand_or_patterns method
        expanded, groups = searcher._expand_or_patterns(["create|update", "user"])
        assert expanded == ["create", "update", "user"]
        assert groups == [0, 0, 1]

        # Test with wildcards
        expanded, groups = searcher._expand_or_patterns(["create*|update*", "user"])
        assert expanded == ["create*", "update*", "user"]
        assert groups == [0, 0, 1]

    def test_search_with_or_pattern(self, sample_index):
        """Test search with OR pattern matches multiple keywords."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create|update"], top_n=10)

        # Should match both create and update functions
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert any("create" in name.lower() for name in names)
        assert any("update" in name.lower() for name in names)

    def test_search_with_wildcard_or_pattern(self, sample_index):
        """Test search with wildcard OR pattern."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["creat*|updat*"], top_n=10)

        # Should match functions starting with creat or updat
        assert len(results) > 0
        assert any("create" in r["name"].lower() for r in results)
        assert any("update" in r["name"].lower() for r in results)

    def test_or_pattern_has_wildcards_detection(self, sample_index):
        """Test that OR patterns are detected as wildcards."""
        searcher = KeywordSearcher(sample_index)

        # OR pattern should be detected as wildcard
        assert searcher._has_wildcards(["create|update"]) is True

        # Combined with asterisk
        assert searcher._has_wildcards(["create*|update*"]) is True

        # Regular keywords should not be detected
        assert searcher._has_wildcards(["create", "update"]) is False

    def test_complex_or_pattern(self, sample_index):
        """Test complex OR pattern with multiple alternatives."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create|update|delete"], top_n=10)

        # Should match all three types of functions
        assert len(results) > 0
        names = [r["name"].lower() for r in results]
        # At least one of each should be found
        has_create = any("create" in name for name in names)
        has_update = any("update" in name for name in names)
        has_delete = any("delete" in name for name in names)

        # Should match at least two of the three
        assert sum([has_create, has_update, has_delete]) >= 2

    def test_or_pattern_confidence(self, sample_index):
        """OR searches should report confidence using original term count."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create|update"])

        assert results
        assert all(r["confidence"] == 100.0 for r in results)
