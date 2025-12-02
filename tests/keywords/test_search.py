"""Tests for keyword search functionality."""

import pytest

from cicada.keyword_search import KeywordSearcher
from cicada.mcp.pattern_utils import has_wildcards, match_wildcard


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
                            "comment_keywords": {"todo": 0.9},
                            "comment_sources": [
                                {
                                    "comment": "TODO remove test data",
                                    "line": 35,
                                    "start_line": 35,
                                    "end_line": 35,
                                }
                            ],
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
        """Test has_wildcards function."""
        # Test individual patterns
        assert has_wildcards("user*") is True
        assert has_wildcards("*user") is True
        assert has_wildcards("user") is False
        assert has_wildcards("create*") is True
        assert has_wildcards("user|account") is True  # OR patterns also count as wildcards

    def test_match_wildcard(self, sample_index):
        """Test match_wildcard function."""
        assert match_wildcard("user*", "user") is True
        assert match_wildcard("user*", "username") is True
        assert match_wildcard("*user", "myuser") is True
        assert match_wildcard("cr*ate", "create") is True
        assert match_wildcard("user*", "account") is False
        # Question mark should not work as wildcard
        assert match_wildcard("user?", "users") is False

    def test_multiple_wildcard_patterns(self, sample_index):
        """Test search with multiple wildcard patterns."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["creat*", "*user"])

        assert len(results) > 0
        # Should match functions with both patterns
        assert any(r["confidence"] > 50 for r in results)

    def test_wildcard_case_insensitive(self, sample_index):
        """Test that wildcard matching is case insensitive."""
        assert match_wildcard("USER*", "username") is True
        assert match_wildcard("user*", "USERNAME") is True

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

    def test_invalid_match_source(self, sample_index):
        """Ensure invalid match_source raises a clear error."""
        with pytest.raises(ValueError):
            KeywordSearcher(sample_index, match_source="invalid")

    def test_search_comments_only(self, sample_index):
        """Search using only comment keywords."""
        searcher = KeywordSearcher(sample_index, match_source="comments")
        results = searcher.search(["todo"])

        assert any("delete_user" in r["name"] for r in results)
        for result in results:
            # Sources should indicate comments only
            assert all(src == "comments" for src in result["keyword_sources"].values())

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
        """Test hybrid scoring with diverse keywords (no repetition)."""
        searcher = KeywordSearcher(sample_index)
        # Search for "create" and "user" should match MyApp.User.create/1
        # which has create: 0.8, user: 0.9
        results = searcher.search(["create", "user"], top_n=10)

        assert len(results) > 0
        # Find the create/1 function
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None
        # Base score: 0.8 + 0.9 = 1.7
        # Coverage: 2/2 = 100% → multiplier = 0.8 + 0.8 = 1.6
        # Final score: 1.7 × 1.6 = 2.72
        assert abs(create_result["score"] - 2.72) < 0.01

    def test_diminishing_returns_repeated_keyword(self, sample_index):
        """Test that repeated keywords get diminishing returns."""
        searcher = KeywordSearcher(sample_index)
        # Search with repeated "create" keyword
        # MyApp.User.create/1 has create: 0.8
        results = searcher.search(["create", "create", "create"], top_n=10)

        assert len(results) > 0
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None

        # Base score with diminishing returns:
        # 1st match: 0.8 × 1.0 = 0.8
        # 2nd match: 0.8 × 0.5 = 0.4
        # 3rd match: 0.8 × 0.25 = 0.2
        # Total base: 1.4
        # Coverage: 1/1 unique = 100% → multiplier = 1.6
        # Final: 1.4 × 1.6 = 2.24
        assert abs(create_result["score"] - 2.24) < 0.01

    def test_coverage_bonus_diverse_keywords(self, sample_index):
        """Test that diverse keywords get coverage bonus over repetition."""
        searcher = KeywordSearcher(sample_index)

        # Search 1: Repeated keyword ["create", "create", "create"]
        # Expected score: ~2.24 (from test above)
        repeated_results = searcher.search(["create", "create", "create"], top_n=10)
        repeated_score = next(
            (r["score"] for r in repeated_results if r["name"] == "MyApp.User.create/1"), None
        )

        # Search 2: Diverse keywords ["create", "user"]
        # Expected score: ~2.72 (from test_score_calculation_simple)
        diverse_results = searcher.search(["create", "user"], top_n=10)
        diverse_score = next(
            (r["score"] for r in diverse_results if r["name"] == "MyApp.User.create/1"), None
        )

        # Diverse keywords should score higher despite having same base weight sum
        assert diverse_score is not None
        assert repeated_score is not None
        assert diverse_score > repeated_score

        # Verify the approximate ratio
        # diverse: 2.72 vs repeated: 2.24 → ~21% higher
        assert diverse_score / repeated_score > 1.2

    def test_partial_coverage_penalty(self, sample_index):
        """Test that partial keyword coverage reduces the multiplier."""
        searcher = KeywordSearcher(sample_index)

        # Search with 3 keywords, only 2 match
        # MyApp.User.create/1 has create: 0.8, user: 0.9
        results = searcher.search(["create", "user", "nonexistent"], top_n=10)

        assert len(results) > 0
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None

        # Base score: 0.8 + 0.9 = 1.7
        # Coverage: 2/3 unique matched = 66.67% → multiplier = 0.8 + (0.667 × 0.8) = 1.333
        # Final: 1.7 × 1.333 = 2.267
        assert abs(create_result["score"] - 2.267) < 0.05

    def test_hybrid_scoring_edge_case_single_keyword(self, sample_index):
        """Test hybrid scoring with single keyword (100% coverage)."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create"], top_n=10)

        assert len(results) > 0
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None

        # Base score: 0.8
        # Coverage: 1/1 = 100% → multiplier = 1.6
        # Final: 0.8 × 1.6 = 1.28
        assert abs(create_result["score"] - 1.28) < 0.01

    def test_hybrid_scoring_zero_coverage(self, sample_index):
        """Test hybrid scoring when no keywords match (edge case)."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["nonexistent", "alsononexistent"], top_n=10)

        # Should return empty results
        assert len(results) == 0

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

        # Test _process_keyword_groups method
        expanded, groups = searcher._process_keyword_groups(["create|update", "user"])
        assert expanded == ["create", "update", "user"]
        assert groups == [0, 0, 1]

        # Test with wildcards
        expanded, groups = searcher._process_keyword_groups(["create*|update*", "user"])
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
        # OR pattern should be detected as wildcard
        assert has_wildcards("create|update") is True

        # Combined with asterisk
        assert has_wildcards("create*|update*") is True

        # Regular keywords should not be detected
        assert has_wildcards("create") is False
        assert has_wildcards("update") is False

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

    def test_module_qualified_keyword(self, sample_index):
        """Test search with module-qualified keyword (e.g., ApiKeys.create_user)."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["MyApp.User.create"], top_n=10)

        # Should boost results from MyApp.User module
        assert len(results) > 0
        # Find the MyApp.User result
        user_result = next((r for r in results if r["module"] == "MyApp.User"), None)
        assert user_result is not None
        assert "module_matched" in user_result
        assert user_result["module_matched"] is True

        # User module result should have higher score than without module match
        # (it gets a +2.0 boost)

    def test_module_extraction_simple(self, sample_index):
        """Test _extract_module_patterns with simple module name."""
        searcher = KeywordSearcher(sample_index)
        patterns = searcher._extract_module_patterns(["apikeys.create_user"])

        assert "apikeys" in patterns

    def test_module_extraction_nested(self, sample_index):
        """Test _extract_module_patterns with nested module."""
        searcher = KeywordSearcher(sample_index)
        patterns = searcher._extract_module_patterns(["myapp.user.create_user"])

        # Should extract both the full module and wildcard pattern
        assert "myapp.user" in patterns
        assert "myapp.*" in patterns

    def test_module_extraction_wildcard(self, sample_index):
        """Test _extract_module_patterns with wildcard in module."""
        searcher = KeywordSearcher(sample_index)
        patterns = searcher._extract_module_patterns(["myapp.*.create"])

        assert "myapp.*" in patterns

    def test_module_extraction_no_dots(self, sample_index):
        """Test _extract_module_patterns with keywords without dots."""
        searcher = KeywordSearcher(sample_index)
        patterns = searcher._extract_module_patterns(["create", "user"])

        # Should return empty list since no keywords have dots
        assert len(patterns) == 0

    def test_match_module_name_exact(self, sample_index):
        """Test _match_module_name with exact match."""
        searcher = KeywordSearcher(sample_index)

        assert searcher._match_module_name("myapp.user", "MyApp.User") is True
        assert searcher._match_module_name("myapp.post", "MyApp.User") is False

    def test_match_module_name_wildcard(self, sample_index):
        """Test _match_module_name with wildcard."""
        searcher = KeywordSearcher(sample_index)

        assert searcher._match_module_name("myapp.*", "MyApp.User") is True
        assert searcher._match_module_name("myapp.*", "MyApp.Post") is True
        assert searcher._match_module_name("otherapp.*", "MyApp.User") is False

    def test_module_qualified_search_boosts_score(self, sample_index):
        """Test that module-qualified searches boost the score."""
        searcher = KeywordSearcher(sample_index)

        # Search without module qualification
        results_no_module = searcher.search(["create"], top_n=10)
        create_user_score = next(
            (r["score"] for r in results_no_module if r["name"] == "MyApp.User.create/1"), None
        )

        # Search with module qualification
        results_with_module = searcher.search(["MyApp.User.create"], top_n=10)
        create_user_with_module_score = next(
            (r["score"] for r in results_with_module if r["name"] == "MyApp.User.create/1"), None
        )

        # Module-qualified search should have higher score
        assert create_user_with_module_score is not None
        assert create_user_score is not None
        assert create_user_with_module_score > create_user_score

    def test_module_qualified_changes_ranking(self, sample_index):
        """Test that module qualification changes result ranking."""
        searcher = KeywordSearcher(sample_index)

        # Both modules have a "create" function, search with module qualifier
        results = searcher.search(["MyApp.Post.create"], top_n=10)

        # MyApp.Post.create/1 should be ranked first due to module match
        assert len(results) > 0
        assert results[0]["module"] == "MyApp.Post"
        assert "module_matched" in results[0]

    def test_multiple_module_qualified_keywords(self, sample_index):
        """Test search with multiple module-qualified keywords."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["MyApp.User.create", "MyApp.Post.publish"], top_n=10)

        # Should find results from both modules with boosts
        assert len(results) > 0
        user_results = [r for r in results if r["module"] == "MyApp.User"]
        post_results = [r for r in results if r["module"] == "MyApp.Post"]

        assert len(user_results) > 0
        assert len(post_results) > 0

    def test_module_qualified_with_wildcard_module(self, sample_index):
        """Test module qualification with wildcard in module name."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["MyApp.*.create"], top_n=10)

        # Should boost all functions in MyApp.* modules
        assert len(results) > 0
        # All results should be from MyApp modules
        assert all(r["module"].startswith("MyApp") for r in results)
        # All should have module_matched flag
        assert all(r.get("module_matched", False) for r in results)

    def test_module_qualified_or_pattern(self, sample_index):
        """Test module-qualified keywords with OR patterns."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["MyApp.User.create|MyApp.Post.create"], top_n=10)

        # Should find create functions from both modules
        assert len(results) > 0
        modules_found = {r["module"] for r in results}
        assert "MyApp.User" in modules_found
        assert "MyApp.Post" in modules_found

    def test_string_keywords_search(self):
        """Test search with string_keywords field."""
        index = {
            "modules": {
                "MyApp.SQL": {
                    "file": "lib/sql.ex",
                    "line": 1,
                    "keywords": {"sql": 0.8},
                    "string_keywords": {"select": 1.04, "users": 0.97},
                    "functions": [
                        {
                            "name": "query",
                            "arity": 1,
                            "line": 10,
                            "keywords": {"query": 0.8},
                            "string_keywords": {"select": 1.17, "from": 1.04},
                        }
                    ],
                }
            }
        }
        searcher = KeywordSearcher(index, match_source="strings")
        results = searcher.search(["select"], top_n=10)
        assert len(results) > 0
        assert any(r["name"] == "MyApp.SQL.query/1" for r in results)

    def test_match_source_docs_only(self):
        """Test match_source='docs' filters to only doc keywords."""
        index = {
            "modules": {
                "MyApp.SQL": {
                    "file": "lib/sql.ex",
                    "line": 1,
                    "keywords": {"sql": 0.8},
                    "string_keywords": {"select": 1.04},
                    "functions": [],
                }
            }
        }
        searcher = KeywordSearcher(index, match_source="docs")
        results = searcher.search(["sql"], top_n=10)
        assert len(results) > 0

        # Should not match string keywords
        results2 = searcher.search(["select"], top_n=10)
        assert len(results2) == 0

    def test_match_source_all_default(self):
        """Test match_source='all' searches both doc and string keywords."""
        index = {
            "modules": {
                "MyApp.SQL": {
                    "file": "lib/sql.ex",
                    "line": 1,
                    "keywords": {"sql": 0.8},
                    "string_keywords": {"select": 1.04},
                    "functions": [],
                }
            }
        }
        searcher = KeywordSearcher(index, match_source="all")
        doc_results = searcher.search(["sql"], top_n=10)
        string_results = searcher.search(["select"], top_n=10)
        assert len(doc_results) > 0
        assert len(string_results) > 0
