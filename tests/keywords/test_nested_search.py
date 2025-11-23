"""Tests for nested keyword search functionality."""

import pytest

from cicada.keyword_search import KeywordSearcher


class TestNestedKeywordSearch:
    """Test nested list support in KeywordSearcher."""

    @pytest.fixture
    def sample_index(self):
        """Create a sample index for testing."""
        return {
            "modules": {
                "MyApp.Auth": {
                    "file": "lib/my_app/auth.ex",
                    "line": 1,
                    "moduledoc": "Authentication module",
                    "keywords": ["auth", "login", "security"],
                    "functions": [
                        {
                            "name": "login",
                            "arity": 1,
                            "line": 10,
                            "doc": "Logs in a user",
                            "keywords": {"login": 0.9, "signin": 0.8, "auth": 0.7},
                        },
                        {
                            "name": "verify",
                            "arity": 1,
                            "line": 20,
                            "doc": "Verifies token",
                            "keywords": {"verify": 0.8, "check": 0.7, "token": 0.9},
                        },
                    ],
                },
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User management",
                    "keywords": ["user", "account", "profile"],
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Create user",
                            "keywords": {"create": 0.8, "user": 0.9, "new": 0.7},
                        },
                    ],
                },
            }
        }

    def test_synonyms_sum_scores(self, sample_index):
        """Test that synonyms in nested list sum their scores."""
        searcher = KeywordSearcher(sample_index)

        # Search for "login" (score 0.9)
        results_single = searcher.search(["login"])
        score_single = results_single[0]["score"]

        # Search for "auth" (score 0.7)
        results_auth = searcher.search(["auth"])
        score_auth = results_auth[0]["score"]

        # Search for ["login", "auth"] (nested) -> should sum scores
        results_nested = searcher.search([["login", "auth"]])
        score_nested = results_nested[0]["score"]

        # Score should be approximately sum (1.6)
        assert score_nested > score_single
        assert score_nested > score_auth
        assert abs(score_nested - (score_single + score_auth)) < 0.01

    def test_synonyms_single_confidence_group(self, sample_index):
        """Test that synonyms count as single group for confidence."""
        searcher = KeywordSearcher(sample_index)

        # Query: [["login", "auth"]] -> 1 group
        # Result matches both.
        # Confidence should be 100% (1/1 matched)
        results = searcher.search([["login", "auth"]])
        assert results[0]["confidence"] == 100.0

        # Query: ["login", "auth"] -> 2 groups (separate)
        # Result matches both.
        # Confidence should be 100% (2/2 matched)
        results_separate = searcher.search(["login", "auth"])
        assert results_separate[0]["confidence"] == 100.0

        # Query: [["login", "auth"], "token"] -> 2 groups
        # Result matches "login" and "auth" but NOT "token" (for login/1 function)
        # Matched groups: {0} (from login and auth)
        # Total groups: 2
        # Confidence: 50%
        results_partial = searcher.search([["login", "auth"], "token"])
        login_result = next(r for r in results_partial if r["name"] == "MyApp.Auth.login/1")
        assert login_result["confidence"] == 50.0

    def test_mixed_input_format(self, sample_index):
        """Test mixed string and list input."""
        searcher = KeywordSearcher(sample_index)

        # ["user", ["login", "signin"]]
        # user matches (group 0)
        # login matches (group 1)
        # signin matches (group 1)
        results = searcher.search(["user", ["login", "signin"]])

        # Should find login/1 function (matches login/signin but NOT user - wait, login/1 has user?)
        # login/1 keywords: login: 0.9, signin: 0.8, auth: 0.7. (No "user")
        # So for login/1: group 1 matches. group 0 (user) does not.
        # Confidence: 50%.

        login_result = next((r for r in results if r["name"] == "MyApp.Auth.login/1"), None)
        assert login_result is not None
        assert login_result["confidence"] == 50.0

        # MyApp.User.create matches "user". Does it match login/signin? No.
        # So confidence 50%.
        create_result = next((r for r in results if r["name"] == "MyApp.User.create/1"), None)
        assert create_result is not None
        assert create_result["confidence"] == 50.0

    def test_wildcards_in_nested_list(self, sample_index):
        """Test wildcards inside nested lists."""
        searcher = KeywordSearcher(sample_index)

        # [["log*", "sign*"]]
        # Should match "login" and "signin"
        results = searcher.search([["log*", "sign*"]])

        login_result = next((r for r in results if r["name"] == "MyApp.Auth.login/1"), None)
        assert login_result is not None
        # Should match both patterns and sum scores
        # login matches log* -> 0.9
        # signin matches sign* -> 0.8
        # Total ~ 1.7
        assert login_result["score"] > 1.0

    def test_or_syntax_in_nested_list(self, sample_index):
        """Test | syntax inside nested list strings."""
        searcher = KeywordSearcher(sample_index)

        # [["login|signin"]] -> equivalent to [["login", "signin"]]
        results = searcher.search([["login|signin"]])

        login_result = next((r for r in results if r["name"] == "MyApp.Auth.login/1"), None)
        assert login_result is not None
        assert login_result["score"] > 1.0  # Sum of login(0.9) and signin(0.8)

    def test_module_boost_in_nested_list(self, sample_index):
        """Test module extraction from nested list."""
        searcher = KeywordSearcher(sample_index)

        # [["MyApp.Auth.login", "MyApp.Auth.signin"]]
        # Should boost MyApp.Auth module matches
        results = searcher.search([["MyApp.Auth.login", "MyApp.Auth.signin"]])

        login_result = next((r for r in results if r["name"] == "MyApp.Auth.login/1"), None)
        assert login_result is not None
        assert login_result.get("module_matched") is True
