"""
Extended tests for KeywordSearcher - covers match details and co-change boost.

Covers:
- _analyze_match_details for detailed location analysis
- _apply_cochange_boost for function-level boosting
- _find_module_by_file for module lookup
- _resolve_cochange_files for co-change file resolution
"""

import pytest

from cicada.keyword_search import KeywordSearcher


@pytest.fixture
def sample_index():
    """Create a sample index with keywords and co-change data."""
    return {
        "metadata": {"total_modules": 2},
        "modules": {
            "MyApp.Auth": {
                "name": "MyApp.Auth",
                "file": "lib/my_app/auth.ex",
                "line": 1,
                "doc": "Authentication module for user login and session management",
                "keywords": {"authentication": 0.9, "login": 0.8, "user": 0.7},
                "cochange_files": [
                    {"file": "lib/my_app/user.ex", "count": 15},
                    {"file": "lib/my_app/session.ex", "count": 8},
                ],
                "functions": [
                    {
                        "name": "authenticate",
                        "arity": 2,
                        "line": 10,
                        "doc": "Authenticate user with password",
                        "keywords": {"authenticate": 0.95, "password": 0.85, "user": 0.8},
                        "string_sources": [
                            {"string": "SELECT * FROM users WHERE email = ?", "line": 15},
                            {"string": "Invalid password", "line": 20},
                        ],
                        "cochange_functions": [
                            {"module": "MyApp.User", "function": "get", "arity": 1, "count": 10},
                            {
                                "module": "MyApp.Session",
                                "function": "create",
                                "arity": 2,
                                "count": 5,
                            },
                        ],
                    },
                    {
                        "name": "validate_token",
                        "arity": 1,
                        "line": 50,
                        "doc": "Validate a session token",
                        "keywords": {"validate": 0.9, "token": 0.88},
                    },
                ],
            },
            "MyApp.User": {
                "name": "MyApp.User",
                "file": "lib/my_app/user.ex",
                "line": 1,
                "doc": "User management module",
                "keywords": {"user": 0.95, "management": 0.7},
                "functions": [
                    {
                        "name": "get",
                        "arity": 1,
                        "line": 10,
                        "doc": "Get user by ID",
                        "keywords": {"get": 0.9, "user": 0.8, "id": 0.75},
                    },
                ],
            },
        },
    }


@pytest.fixture
def searcher(sample_index):
    """Create a KeywordSearcher with the sample index."""
    return KeywordSearcher(sample_index, match_source="all", cochange_boost=0.5)


class TestMatchDetailAnalysis:
    """Test detailed match location analysis."""

    def test_analyze_match_in_name(self, searcher):
        """Test analyzing keyword matches in name."""
        doc = {
            "name": "authenticate_user",
            "doc": "",
        }

        result = searcher._analyze_match_details(["user"], doc)

        assert "user" in result
        assert result["user"]["total_count"] == 1
        locations = result["user"]["locations"]
        assert any(loc["type"] == "name" for loc in locations)

    def test_analyze_match_in_doc(self, searcher):
        """Test analyzing keyword matches in documentation."""
        doc = {
            "name": "auth",
            "doc": "User authentication module for user management",
        }

        result = searcher._analyze_match_details(["user"], doc)

        assert "user" in result
        # "user" appears twice in doc
        assert result["user"]["total_count"] >= 2
        locations = result["user"]["locations"]
        assert any(loc["type"] == "doc" for loc in locations)

    def test_analyze_match_in_strings(self, searcher):
        """Test analyzing keyword matches in string literals."""
        doc = {
            "name": "query",
            "doc": "",
            "string_sources": [
                {"string": "SELECT * FROM users", "line": 10},
                {"string": "INSERT INTO users", "line": 20},
            ],
        }

        result = searcher._analyze_match_details(["users"], doc)

        assert "users" in result
        assert result["users"]["total_count"] == 2
        locations = result["users"]["locations"]
        string_loc = next((loc for loc in locations if loc["type"] == "string"), None)
        assert string_loc is not None
        assert string_loc["lines"] == [10, 20]

    def test_analyze_multiple_keywords(self, searcher):
        """Test analyzing multiple keywords."""
        doc = {
            "name": "user_auth",
            "doc": "Authentication for users",
        }

        result = searcher._analyze_match_details(["user", "auth"], doc)

        assert "user" in result
        assert "auth" in result
        # Both should have matches
        assert result["user"]["total_count"] > 0
        assert result["auth"]["total_count"] > 0

    def test_analyze_no_matches(self, searcher):
        """Test that unmatched keywords are not included."""
        doc = {
            "name": "foo",
            "doc": "bar",
        }

        result = searcher._analyze_match_details(["xyz"], doc)

        assert "xyz" not in result


class TestCochangeBoost:
    """Test co-change boost functionality."""

    def test_module_level_boost(self, searcher):
        """Test co-change boost for module results."""
        results = [
            {
                "type": "module",
                "module": "MyApp.Auth",
                "score": 1.0,
            }
        ]

        boosted = searcher._apply_cochange_boost(results)

        # Score should be boosted due to cochange_files
        assert boosted[0]["score"] > 1.0
        # Should have cochange_info
        assert "cochange_info" in boosted[0]
        assert "related_files" in boosted[0]["cochange_info"]

    def test_function_level_boost(self, searcher):
        """Test co-change boost for function results."""
        results = [
            {
                "type": "function",
                "module": "MyApp.Auth",
                "function": "authenticate",
                "arity": 2,
                "score": 1.0,
            }
        ]

        boosted = searcher._apply_cochange_boost(results)

        # Score should be boosted due to cochange_functions
        assert boosted[0]["score"] > 1.0
        # Should have cochange_info with both files and functions
        assert "cochange_info" in boosted[0]
        info = boosted[0]["cochange_info"]
        assert "related_functions" in info or "related_files" in info

    def test_function_not_found_no_boost(self, searcher):
        """Test that non-existent function gets no boost."""
        results = [
            {
                "type": "function",
                "module": "MyApp.Auth",
                "function": "nonexistent",
                "arity": 0,
                "score": 1.0,
            }
        ]

        boosted = searcher._apply_cochange_boost(results)

        # Score should not be boosted (no function data found)
        assert boosted[0]["score"] == 1.0

    def test_module_not_found_no_boost(self, searcher):
        """Test that non-existent module gets no boost."""
        results = [
            {
                "type": "module",
                "module": "NonExistent",
                "score": 1.0,
            }
        ]

        boosted = searcher._apply_cochange_boost(results)

        # Score should not be boosted
        assert boosted[0]["score"] == 1.0


class TestModuleByFileLookup:
    """Test finding module by file path."""

    def test_find_exact_match(self, searcher):
        """Test finding module with exact file path."""
        result = searcher._find_module_by_file("lib/my_app/auth.ex")

        assert result == "MyApp.Auth"

    def test_find_partial_match(self, searcher):
        """Test finding module with partial file path."""
        result = searcher._find_module_by_file("auth.ex")

        assert result == "MyApp.Auth"

    def test_find_not_found(self, searcher):
        """Test returning None for unknown file."""
        result = searcher._find_module_by_file("nonexistent.ex")

        assert result is None


class TestResolveCochangeFiles:
    """Test resolving co-change files with module names."""

    def test_resolve_adds_module_names(self, searcher):
        """Test that resolution adds module names to files."""
        cochange_files = [
            {"file": "lib/my_app/user.ex", "count": 15},
            {"file": "lib/my_app/unknown.ex", "count": 5},
        ]

        result = searcher._resolve_cochange_files(cochange_files)

        assert len(result) == 2

        # First file should have module resolved
        user_file = next(r for r in result if "user.ex" in r["file"])
        assert user_file["module"] == "MyApp.User"
        assert user_file["count"] == 15

        # Unknown file should have None module
        unknown_file = next(r for r in result if "unknown.ex" in r["file"])
        assert unknown_file["module"] is None


class TestSearchIntegration:
    """Integration tests for search with extended features."""

    def test_search_with_cochange_boost(self, sample_index):
        """Test that search results include co-change boost."""
        searcher = KeywordSearcher(sample_index, cochange_boost=1.0)

        results = searcher.search(["user"], top_n=5, filter_type="all")

        # Should find results
        assert len(results) > 0
        # At least some results should have cochange_info
        has_cochange = any("cochange_info" in r for r in results)
        assert has_cochange

    def test_search_without_cochange_boost(self, sample_index):
        """Test that search works with cochange_boost=0."""
        searcher = KeywordSearcher(sample_index, cochange_boost=0.0)

        results = searcher.search(["user"], top_n=5, filter_type="all")

        # Should still find results
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
