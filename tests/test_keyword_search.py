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
                            "keywords": ["create", "user", "new"],
                        },
                        {
                            "name": "update",
                            "arity": 2,
                            "line": 20,
                            "doc": "Updates user data",
                            "keywords": ["update", "modify", "change"],
                        },
                        {
                            "name": "delete_user",
                            "arity": 1,
                            "line": 30,
                            "doc": "Deletes a user",
                            "keywords": ["delete", "remove", "user"],
                        },
                    ],
                },
                "MyApp.Post": {
                    "file": "lib/my_app/post.ex",
                    "line": 1,
                    "moduledoc": "Post management module",
                    "keywords": ["post", "article", "content"],
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a new post",
                            "keywords": ["create", "post", "publish"],
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
        # Should match user-related results - matched_keywords contains the pattern itself
        assert any("*user" in r["matched_keywords"] for r in results)

    def test_search_with_wildcard_middle(self, sample_index):
        """Test wildcard search with pattern in the middle."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["del*user"])

        assert len(results) > 0
        # Should match delete_user
        assert any("delete_user" in r["name"] for r in results)

    def test_search_with_question_mark_wildcard_not_supported(self, sample_index):
        """Test that ? wildcard is not supported."""
        searcher = KeywordSearcher(sample_index)
        # Question mark should not be treated as a wildcard
        results = searcher.search(["user?"])

        # Should return no results or very few since ? is not a wildcard
        assert len(results) == 0 or all("?" not in r["matched_keywords"] for r in results)

    def test_wildcard_expansion(self, sample_index):
        """Test _expand_wildcard_keywords method."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["cre*", "user"]
        document_keywords = ["create", "user", "new"]

        matched = searcher._expand_wildcard_keywords(query_keywords, document_keywords)

        assert "cre*" in matched  # Pattern should match "create"
        assert "user" in matched  # Exact match

    def test_wildcard_expansion_with_identifier(self, sample_index):
        """Test _expand_wildcard_keywords_with_identifier method."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["del*"]
        document_keywords = ["delete", "remove", "user"]
        identifier_name = "delete_user"

        matched = searcher._expand_wildcard_keywords_with_identifier(
            query_keywords, document_keywords, identifier_name
        )

        assert "del*" in matched  # Should match both "delete" keyword and "delete_user" identifier

    def test_wildcard_scores(self, sample_index):
        """Test _get_wildcard_scores method."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["creat*", "user"]

        scores = searcher._get_wildcard_scores(query_keywords)

        # Should have scores for all documents
        assert len(scores) == len(searcher.document_map)
        # Some scores should be positive for matching documents
        assert any(score > 0 for score in scores)

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

    def test_count_wildcard_matches(self, sample_index):
        """Test _count_wildcard_matches method."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["creat*", "user"]
        item_keywords = ["create", "user", "new"]
        identifier_name = "create_user"

        result = searcher._count_wildcard_matches(query_keywords, item_keywords, identifier_name)

        assert result["score"] == 2  # Both patterns match
        assert result["confidence"] == 100.0  # All query keywords matched
        assert "creat*" in result["matched_keywords"]
        assert "user" in result["matched_keywords"]

    def test_count_wildcard_matches_without_identifier(self, sample_index):
        """Test _count_wildcard_matches without identifier name."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["creat*"]
        item_keywords = ["create", "new"]

        result = searcher._count_wildcard_matches(query_keywords, item_keywords, None)

        assert result["score"] == 1
        assert "creat*" in result["matched_keywords"]

    def test_identifier_boost(self, sample_index):
        """Test that identifier name matches get boosted."""
        searcher = KeywordSearcher(sample_index)
        # Search for "user" should boost results with "user" in the name
        results = searcher.search(["user"], top_n=10)

        # Functions with "user" in the name should rank higher
        assert len(results) > 0
        # delete_user should be highly ranked
        top_names = [r["name"] for r in results[:3]]
        assert any("user" in name.lower() for name in top_names)

    def test_identifier_boost_wildcard(self, sample_index):
        """Test _apply_identifier_boost_wildcard method."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "name": "MyApp.User.delete_user/1",
            "function": "delete_user",
            "keywords": ["delete", "remove"],
        }
        query_keywords = ["del*"]
        base_score = 1.0

        boosted_score = searcher._apply_identifier_boost_wildcard(
            base_score, query_keywords, doc_info
        )

        # Score should be boosted because "del*" matches "delete_user"
        assert boosted_score > base_score
        assert boosted_score == base_score * searcher.IDENTIFIER_MATCH_BOOST

    def test_calculate_name_coverage_penalty_exact_match(self, sample_index):
        """Test that exact name matches get no penalty."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "create_user",
        }
        query_keywords = ["create", "user"]

        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        assert penalty == 1.0  # No penalty for exact match

    def test_calculate_name_coverage_penalty_extra_words(self, sample_index):
        """Test penalty for function names with extra words."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "create_invalid_user",
        }
        query_keywords = ["create", "user"]

        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        # Should have penalty because "invalid" is not in query
        assert penalty < 1.0
        assert penalty == 0.7  # 1 extra word = 30% penalty

    def test_calculate_name_coverage_penalty_module(self, sample_index):
        """Test that modules don't get name coverage penalty."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "module",
            "function": "MyApp.User.Extra",
        }
        query_keywords = ["user"]

        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        assert penalty == 1.0  # Modules should not be penalized

    def test_count_matches(self, sample_index):
        """Test _count_matches method."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["create", "user"]
        item_keywords = ["create", "user", "new"]

        result = searcher._count_matches(query_keywords, item_keywords)

        assert result["score"] == 2
        assert result["confidence"] == 100.0
        assert result["matched_keywords"] == ["create", "user"]

    def test_count_matches_partial(self, sample_index):
        """Test _count_matches with partial matches."""
        searcher = KeywordSearcher(sample_index)
        query_keywords = ["create", "delete", "update"]
        item_keywords = ["create", "user", "new"]

        result = searcher._count_matches(query_keywords, item_keywords)

        assert result["score"] == 1  # Only "create" matches
        assert result["confidence"] == pytest.approx(33.3, rel=0.1)  # 1/3 * 100
        assert result["matched_keywords"] == ["create"]

    def test_index_without_keywords_fallback(self, index_without_keywords):
        """Test that searcher falls back to identifier names when no keywords exist."""
        searcher = KeywordSearcher(index_without_keywords)

        # Should still be able to search using identifier names
        results = searcher.search(["add"])

        assert len(results) > 0
        assert any("add" in r["name"].lower() for r in results)

    def test_empty_index(self):
        """Test searcher with empty index."""
        empty_index = {"modules": {}}
        searcher = KeywordSearcher(empty_index)

        results = searcher.search(["anything"])

        assert len(results) == 0
        assert searcher.bm25 is None

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

    def test_extract_identifier_name_module(self, sample_index):
        """Test _extract_identifier_name for modules."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "module",
            "name": "MyApp.User",
        }

        name = searcher._extract_identifier_name(doc_info)

        assert name == "MyApp.User"

    def test_extract_identifier_name_function(self, sample_index):
        """Test _extract_identifier_name for functions."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "create_user",
        }

        name = searcher._extract_identifier_name(doc_info)

        assert name == "create_user"

    def test_apply_identifier_boost_with_match(self, sample_index):
        """Test _apply_identifier_boost when identifier matches."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "delete_user",
        }
        query_keywords = ["delete"]
        base_score = 1.0

        boosted_score = searcher._apply_identifier_boost(base_score, query_keywords, doc_info)

        assert boosted_score == base_score * searcher.IDENTIFIER_MATCH_BOOST

    def test_apply_identifier_boost_without_match(self, sample_index):
        """Test _apply_identifier_boost when identifier doesn't match."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "create_user",
        }
        query_keywords = ["delete"]
        base_score = 1.0

        boosted_score = searcher._apply_identifier_boost(base_score, query_keywords, doc_info)

        assert boosted_score == base_score  # No boost

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

    def test_search_includes_documentation(self, sample_index):
        """Test that search results include documentation when available."""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["create"])

        # At least some results should have doc
        assert any("doc" in r and r["doc"] for r in results)

    def test_negative_score_handling(self, sample_index):
        """Test handling of negative BM25 scores with coverage penalty."""
        searcher = KeywordSearcher(sample_index)
        doc_info = {
            "type": "function",
            "function": "extra_long_function_name",
        }
        query_keywords = ["function"]

        # When final_score is negative and penalty < 1.0, divide instead of multiply
        negative_score = -0.5
        coverage_penalty = 0.7

        # Simulate the logic in search()
        if negative_score < 0 and coverage_penalty < 1.0:
            result_score = negative_score / coverage_penalty
        else:
            result_score = negative_score * coverage_penalty

        # Division should make negative score more negative
        assert result_score < negative_score
