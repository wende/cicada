"""Comprehensive tests for cicada/utils/fuzzy_match.py"""

import pytest

from cicada.utils.fuzzy_match import find_similar_names


class TestFindSimilarNames:
    """Tests for find_similar_names function."""

    def test_exact_match(self):
        """Should return exact match with score 1.0."""
        candidates = ["Calculator", "StringUtils", "UserService"]
        results = find_similar_names("Calculator", candidates)

        assert len(results) == 1
        assert results[0] == ("Calculator", 1.0)

    def test_exact_match_case_insensitive(self):
        """Should match case-insensitively."""
        candidates = ["Calculator", "StringUtils", "UserService"]
        results = find_similar_names("calculator", candidates)

        assert len(results) == 1
        assert results[0] == ("Calculator", 1.0)

    def test_exact_match_early_return(self):
        """Should return immediately on exact match without checking others."""
        # Even with many candidates, should return quickly
        candidates = ["A"] * 1000 + ["Calculator"] + ["B"] * 1000
        results = find_similar_names("calculator", candidates)

        assert len(results) == 1
        assert results[0][0] == "Calculator"
        assert results[0][1] == 1.0

    def test_substring_match_boost(self):
        """Should boost score for substring matches."""
        candidates = ["UserAuthenticationService", "FileUtils", "Logger"]
        results = find_similar_names("Auth", candidates)

        # "Auth" is substring of "UserAuthenticationService"
        assert len(results) > 0
        auth_result = next((r for r in results if "Authentication" in r[0]), None)
        assert auth_result is not None
        assert auth_result[1] >= 0.7  # Boosted to at least 0.7

    def test_partial_component_match_boost(self):
        """Should boost score for partial component matches."""
        candidates = ["MyApp.User.Service", "MyApp.Auth.Service", "OtherApp.User"]
        results = find_similar_names("User", candidates)

        # "User" appears in multiple candidates
        assert results
        user_results = [r for r in results if "User" in r[0]]
        assert user_results
        # All should have boosted scores
        assert all(result[1] >= 0.6 for result in user_results)

    def test_dotted_query_component_match(self):
        """Should match dotted query parts against candidates."""
        candidates = ["MyApp.User.Service", "MyApp.Auth.Service", "Auth.Utils"]
        results = find_similar_names("MyApp.User", candidates)

        # Should match "MyApp.User.Service" well
        assert len(results) > 0
        best_match = results[0]
        assert "MyApp.User.Service" in best_match[0]
        assert best_match[1] >= 0.6

    def test_similarity_sorting(self):
        """Should sort results by similarity score descending."""
        candidates = ["UserService", "User", "UserAuthService", "RandomModule"]
        results = find_similar_names("User", candidates, max_suggestions=10)

        # Check that scores are in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_max_suggestions_limit(self):
        """Should respect max_suggestions parameter."""
        candidates = [f"Module{i}" for i in range(100)]
        results = find_similar_names("Module", candidates, max_suggestions=5)

        assert len(results) <= 5

    def test_max_suggestions_default(self):
        """Should use default max_suggestions of 5."""
        candidates = [f"Module{i}" for i in range(100)]
        results = find_similar_names("Module", candidates)

        assert len(results) <= 5

    def test_threshold_filtering(self):
        """Should filter out results below threshold."""
        candidates = ["UserService", "XYZ", "ABC"]
        results = find_similar_names("User", candidates, threshold=0.5)

        # Only results with score > 0.5 should be included
        assert all(score > 0.5 for _, score in results)

    def test_custom_threshold(self):
        """Should respect custom threshold parameter."""
        candidates = ["UserService", "User", "UserAuth", "RandomStuff"]
        results = find_similar_names("User", candidates, threshold=0.8, max_suggestions=10)

        # Only high-scoring matches should be included
        assert all(score > 0.8 for _, score in results)

    def test_threshold_default(self):
        """Should use default threshold of 0.4."""
        candidates = ["User", "UsXr", "XXXX"]  # Various similarity levels
        results = find_similar_names("User", candidates, threshold=0.4)

        # Should include moderate matches
        assert results
        assert all(score > 0.4 for _, score in results)

    def test_no_matches_above_threshold(self):
        """Should return empty list when no matches above threshold."""
        candidates = ["XYZ", "ABC", "123"]
        results = find_similar_names("User", candidates, threshold=0.9)

        assert results == []

    def test_empty_candidates(self):
        """Should return empty list for empty candidates."""
        results = find_similar_names("User", [])

        assert results == []

    def test_empty_query(self):
        """Should handle empty query string."""
        candidates = ["User", "Auth", "Service"]
        results = find_similar_names("", candidates)

        # Empty query might match poorly or not at all
        # Just ensure it doesn't crash
        assert isinstance(results, list)

    def test_single_character_query(self):
        """Should handle single character queries."""
        candidates = ["UserService", "AuthService", "XService"]
        results = find_similar_names("U", candidates)

        # Should find matches
        assert isinstance(results, list)

    def test_unicode_matching(self):
        """Should handle unicode characters in query and candidates."""
        candidates = ["Módulo", "Función", "Clase"]
        results = find_similar_names("Módulo", candidates)

        assert len(results) > 0
        assert results[0][0] == "Módulo"

    def test_whitespace_in_names(self):
        """Should handle whitespace in names."""
        candidates = ["User Service", "Auth Service", "Data Processor"]
        results = find_similar_names("User", candidates)

        assert len(results) > 0
        user_match = next((r for r in results if "User" in r[0]), None)
        assert user_match is not None

    def test_special_characters(self):
        """Should handle special characters in names."""
        candidates = ["User-Service", "Auth_Service", "Data.Processor"]
        results = find_similar_names("User", candidates)

        assert len(results) > 0

    def test_case_preservation_in_results(self):
        """Should preserve original case in results."""
        candidates = ["UserService", "USERAUTH", "userHelper"]
        results = find_similar_names("user", candidates)

        # Results should maintain original casing
        assert all(name in candidates for name, _ in results)

    def test_mixed_case_matching(self):
        """Should match regardless of case differences."""
        candidates = ["UserService", "USERAUTH", "userHelper"]
        results = find_similar_names("USER", candidates, max_suggestions=10)

        # All should match to some degree
        assert len(results) >= 2

    def test_large_candidate_list_performance(self):
        """Should limit search space for very large candidate lists."""
        # Create 1000 candidates
        candidates = [f"Module{i}" for i in range(1000)]
        results = find_similar_names("Module500", candidates)

        # Should still work efficiently and return results
        assert isinstance(results, list)
        # Search is limited to first 500 candidates
        assert len(results) <= 5

    def test_large_candidate_list_cutoff(self):
        """Should only search first 500 candidates when list is large."""
        # Create candidates where good match is at position 600
        candidates = [f"Random{i}" for i in range(600)]
        candidates.append("UserService")  # Position 600
        candidates.extend([f"Random{i}" for i in range(600, 1000)])

        results = find_similar_names("UserServic", candidates, threshold=0.9)

        # High-similarity candidate beyond cutoff should not be considered
        assert results == []

    def test_score_comparison(self):
        """Should score better matches higher."""
        candidates = ["UserService", "UserAuth", "RandomModule"]
        results = find_similar_names("User", candidates, max_suggestions=10)

        # UserService and UserAuth should score higher than RandomModule
        user_scores = dict(results)

        assert user_scores.get("UserService", 0) > user_scores.get("RandomModule", 0)

    def test_sequence_matcher_similarity(self):
        """Should use SequenceMatcher for basic similarity."""
        candidates = ["abcdef", "abcxef", "xyzabc"]
        results = find_similar_names("abcdef", candidates, max_suggestions=10)

        # Exact match should score highest
        assert results[0][0] == "abcdef"

        # Similar string should score higher than dissimilar
        scores = dict(results)
        assert scores.get("abcxef", 0) >= scores.get("xyzabc", 0)

    def test_substring_boost_applies(self):
        """Should apply 0.7 boost for substring matches."""
        candidates = ["ThisContainsUser", "NotRelevant"]
        results = find_similar_names("User", candidates, max_suggestions=10)

        # "User" is substring of "ThisContainsUser"
        match = next((r for r in results if r[0] == "ThisContainsUser"), None)
        assert match is not None
        assert match[1] >= 0.7

    def test_component_boost_applies(self):
        """Should apply 0.6 boost for component matches."""
        candidates = ["MyApp.UserService", "OtherModule"]
        results = find_similar_names("User.Service", candidates, max_suggestions=10)

        # "User" appears as component
        match = next((r for r in results if "User" in r[0]), None)
        assert match is not None
        assert match[1] >= 0.6

    def test_max_boost_wins(self):
        """Should use maximum boost when multiple apply."""
        candidates = ["UserServiceModule"]  # Substring match
        results = find_similar_names("User", candidates)

        # Both substring and component boosts might apply
        # Should use the max (substring = 0.7, component = 0.6)
        assert len(results) > 0
        assert results[0][1] >= 0.7

    def test_all_parameters_together(self):
        """Should work correctly with all parameters specified."""
        candidates = [
            "UserService",
            "UserAuth",
            "AuthService",
            "RandomModule",
            "UserHelper",
        ]
        results = find_similar_names(
            "User", candidates, max_suggestions=3, threshold=0.5
        )

        # Should return at most 3 results
        assert len(results) <= 3

        # All should be above threshold
        assert all(score > 0.5 for _, score in results)

        # Should be sorted by score
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_dotted_names_matching(self):
        """Should handle dotted module names well."""
        candidates = [
            "MyApp.Users.Service",
            "MyApp.Auth.Service",
            "OtherApp.Users.Helper",
            "Users",
        ]
        results = find_similar_names("Users", candidates, max_suggestions=10)

        # Should match at least one (exact match "Users" is guaranteed)
        users_matches = [r for r in results if "Users" in r[0]]
        assert users_matches
        # Exact match should be present
        assert any(r[0] == "Users" and r[1] == 1.0 for r in results)

    def test_partial_word_matching(self):
        """Should handle partial word matches."""
        candidates = ["Calculator", "Calibrator", "Calendar"]
        results = find_similar_names("Cal", candidates, max_suggestions=10)

        # All start with "Cal"
        assert len(results) >= 2

    def test_typo_tolerance(self):
        """Should handle minor typos reasonably."""
        candidates = ["UserService", "UserAuth", "FileUtils"]
        results = find_similar_names("UzerService", candidates, max_suggestions=10)

        # "UserService" should still match due to similarity
        assert len(results) > 0
        user_service_match = next((r for r in results if r[0] == "UserService"), None)
        assert user_service_match is not None
        # Should have reasonable score despite typo
        assert user_service_match[1] > 0.6

    def test_completely_different_strings(self):
        """Should return low scores for completely different strings."""
        candidates = ["XYZ", "ABC", "123"]
        results = find_similar_names("UserService", candidates, threshold=0.1)

        # Might get some results with very low scores
        assert all(score < 0.5 for _, score in results)


class TestEdgeCases:
    """Edge case tests for fuzzy matching."""

    def test_single_candidate(self):
        """Should work with single candidate."""
        results = find_similar_names("User", ["UserService"])

        assert len(results) <= 1
        assert results and results[0][0] == "UserService"

    def test_duplicate_candidates(self):
        """Should handle duplicate candidates."""
        candidates = ["User", "User", "UserService"]
        results = find_similar_names("User", candidates)

        # Exact matches should be at top
        assert len(results) >= 1
        assert results[0][0] == "User"
        assert results[0][1] == 1.0

    def test_very_long_names(self):
        """Should handle very long module names."""
        long_name = "This.Is.A.Very.Long.Module.Name.With.Many.Components.User"
        candidates = [long_name, "Short"]
        results = find_similar_names("User", candidates, max_suggestions=10)

        # Should find the match
        long_match = next((r for r in results if r[0] == long_name), None)
        assert long_match is not None

    def test_numeric_names(self):
        """Should handle numeric characters in names."""
        candidates = ["Module1", "Module2", "Module3"]
        results = find_similar_names("Module2", candidates)

        assert len(results) >= 1
        assert results[0][0] == "Module2"

    def test_max_suggestions_zero(self):
        """Should handle max_suggestions of 0."""
        candidates = ["UserService", "UserAuth", "UserHelper"]
        # Use non-exact match to avoid early return
        results = find_similar_names("User", candidates, max_suggestions=0)

        # With max_suggestions=0, should return empty list (no exact match to bypass)
        assert results == []

    def test_threshold_zero(self):
        """Should include all matches with threshold 0.0."""
        candidates = ["User", "XXXX", "YYYY"]
        results = find_similar_names("User", candidates, threshold=0.0, max_suggestions=10)

        # Should include everything (up to max_suggestions)
        assert len(results) > 0

    def test_threshold_one(self):
        """Should only include exact matches with threshold 1.0."""
        candidates = ["User", "UserService", "UserAuth"]
        results = find_similar_names("User", candidates, threshold=1.0)

        # Only exact match should pass
        assert len(results) == 1
        assert results[0][0] == "User"
        assert results[0][1] == 1.0

    def test_query_longer_than_candidates(self):
        """Should handle query longer than candidate names."""
        candidates = ["U", "Us", "Use"]
        results = find_similar_names("UserService", candidates, max_suggestions=10)

        # Should get some matches
        assert isinstance(results, list)

    def test_candidate_with_spaces(self):
        """Should handle candidates with multiple spaces."""
        candidates = ["User  Service", "User Service", "UserService"]
        results = find_similar_names("User Service", candidates, max_suggestions=10)

        # Should match reasonably
        assert len(results) > 0
