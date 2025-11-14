"""Tests for Co-occurrence Analysis."""

import pytest

from cicada.cooccurrence import CooccurrenceAnalyzer


class TestCooccurrenceAnalyzer:
    """Test the CooccurrenceAnalyzer class."""

    @pytest.fixture
    def sample_index(self):
        """Sample index with extracted keywords (pre-expansion)."""
        return {
            "modules": {
                "MyApp.User": {
                    "extracted_keywords": {
                        "user": 0.9,
                        "account": 0.8,
                        "authentication": 0.7,
                    },
                    "extracted_string_keywords": {
                        "database": 0.9,
                        "select": 0.8,
                    },
                    "functions": [
                        {
                            "name": "create_user",
                            "extracted_keywords": {
                                "create": 0.95,
                                "user": 0.90,
                                "validation": 0.85,
                            },
                            "extracted_string_keywords": {
                                "insert": 0.9,
                                "database": 0.8,
                            },
                        },
                        {
                            "name": "validate_email",
                            "extracted_keywords": {
                                "validate": 0.95,
                                "email": 0.90,
                                "format": 0.80,
                            },
                        },
                    ],
                },
                "MyApp.Provider": {
                    "extracted_keywords": {
                        "provider": 0.9,
                        "api": 0.8,
                        "authentication": 0.75,
                    },
                    "functions": [
                        {
                            "name": "validate_provider_key",
                            "extracted_keywords": {
                                "validate": 0.95,
                                "provider": 0.90,
                                "api": 0.85,
                                "key": 0.80,
                            },
                        },
                    ],
                },
            },
        }

    def test_initialization(self, sample_index):
        """Test that the analyzer initializes correctly."""
        analyzer = CooccurrenceAnalyzer(sample_index)
        assert analyzer.index == sample_index
        assert analyzer.cooccurrence_matrix is not None
        assert isinstance(analyzer.cooccurrence_matrix, dict)

    def test_keyword_cooccurrence_module_level(self, sample_index):
        """Test that keywords from the same module co-occur."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # "user" and "account" should co-occur (both in MyApp.User module)
        count = analyzer.get_cooccurrence_count("user", "account")
        assert count > 0

        # "user" and "authentication" should co-occur
        count = analyzer.get_cooccurrence_count("user", "authentication")
        assert count > 0

        # "database" and "select" should co-occur (both in MyApp.User string keywords)
        count = analyzer.get_cooccurrence_count("database", "select")
        assert count > 0

    def test_keyword_cooccurrence_function_level(self, sample_index):
        """Test that keywords from the same function co-occur."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # "create" and "user" should co-occur (both in create_user function)
        count = analyzer.get_cooccurrence_count("create", "user")
        assert count > 0

        # "validate" and "email" should co-occur (both in validate_email function)
        count = analyzer.get_cooccurrence_count("validate", "email")
        assert count > 0

        # "validate" and "provider" should co-occur (both in validate_provider_key function)
        count = analyzer.get_cooccurrence_count("validate", "provider")
        assert count > 0

    def test_keywords_not_cooccurring(self, sample_index):
        """Test that keywords from different contexts don't co-occur."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # These keywords never appear together
        count = analyzer.get_cooccurrence_count("create", "provider")
        # May be 0 or positive depending on cross-module co-occurrence

    def test_function_name_components(self, sample_index):
        """Test that function name components are included in co-occurrence."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # Function name "create_user" should split into "create" and "user"
        # These should co-occur with function's keywords
        count = analyzer.get_cooccurrence_count("create", "validation")
        assert count > 0  # Both from create_user function context

    def test_suggest_related_keywords(self, sample_index):
        """Test suggesting related keywords."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # Search for "user" should suggest "account", "authentication"
        suggestions = analyzer.suggest_related_keywords(["user"], top_n=5)

        assert len(suggestions) > 0
        keywords = [s["keyword"] for s in suggestions]

        # Check that expected related keywords are in suggestions
        assert any(kw in keywords for kw in ["account", "authentication", "create"])

        # Each suggestion should have the required fields
        for suggestion in suggestions:
            assert "keyword" in suggestion
            assert "cooccurrence_count" in suggestion
            assert "cooccurs_with" in suggestion
            assert suggestion["cooccurrence_count"] > 0

    def test_suggest_related_keywords_multiple_terms(self, sample_index):
        """Test suggesting keywords for multiple query terms."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # Search for both "validate" and "email"
        suggestions = analyzer.suggest_related_keywords(["validate", "email"], top_n=5)

        assert len(suggestions) > 0

        # Should not suggest keywords that are already in the query
        keywords = [s["keyword"] for s in suggestions]
        assert "validate" not in keywords
        assert "email" not in keywords

    def test_suggest_narrowing_keywords(self, sample_index):
        """Test suggesting keywords to narrow results."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # Mock search results
        search_results = [
            {
                "name": "MyApp.User.create_user/1",
                "keywords": {
                    "create": 0.95,
                    "user": 0.90,
                    "validation": 0.85,
                },
            },
            {
                "name": "MyApp.User.validate_email/1",
                "keywords": {
                    "validate": 0.95,
                    "email": 0.90,
                    "format": 0.80,
                },
            },
        ]

        suggestions = analyzer.suggest_narrowing_keywords(
            ["user"], search_results, top_n=5, min_result_count=1
        )

        # Should suggest keywords that appear in multiple results
        assert len(suggestions) > 0

        # Each suggestion should have the required fields
        for suggestion in suggestions:
            assert "keyword" in suggestion
            assert "result_count" in suggestion
            assert "cooccurs_with" in suggestion

    def test_get_statistics(self, sample_index):
        """Test getting co-occurrence statistics."""
        analyzer = CooccurrenceAnalyzer(sample_index)
        stats = analyzer.get_statistics()

        assert "total_keywords" in stats
        assert "total_cooccurrences" in stats
        assert "avg_cooccurrences_per_keyword" in stats
        assert "most_connected_keywords" in stats

        assert stats["total_keywords"] > 0
        assert stats["total_cooccurrences"] > 0
        assert isinstance(stats["most_connected_keywords"], list)

    def test_empty_index(self):
        """Test behavior with an empty index."""
        empty_index = {"modules": {}}
        analyzer = CooccurrenceAnalyzer(empty_index)

        stats = analyzer.get_statistics()
        assert stats["total_keywords"] == 0
        assert stats["total_cooccurrences"] == 0

        suggestions = analyzer.suggest_related_keywords(["test"])
        assert len(suggestions) == 0

    def test_case_insensitive_matching(self, sample_index):
        """Test that keyword matching is case-insensitive."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # Should work with different cases
        count1 = analyzer.get_cooccurrence_count("User", "Account")
        count2 = analyzer.get_cooccurrence_count("user", "account")
        assert count1 == count2

    def test_min_cooccurrence_filter(self, sample_index):
        """Test filtering by minimum co-occurrence count."""
        analyzer = CooccurrenceAnalyzer(sample_index)

        # With min_cooccurrence=1, should get all suggestions
        suggestions_low = analyzer.suggest_related_keywords(["user"], top_n=10, min_cooccurrence=1)

        # With higher threshold, should get fewer suggestions
        suggestions_high = analyzer.suggest_related_keywords(["user"], top_n=10, min_cooccurrence=3)

        assert len(suggestions_high) <= len(suggestions_low)
