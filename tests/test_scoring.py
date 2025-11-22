"""
Tests for cicada.scoring module.
"""

from cicada.scoring import (
    calculate_score_distribution,
    calculate_score_distribution_with_tiers,
    filter_by_relevance_tier,
    grade_by_z_score,
)


class TestScoreDistribution:
    """Tests for calculate_score_distribution function."""

    def test_basic_distribution_with_float_list(self):
        """Test distribution calculation with a simple list of floats."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 3.0
        assert result["count"] == 5
        assert result["min_score"] == 1.0
        assert result["max_score"] == 5.0
        assert result["std_dev"] > 0  # Should have positive std dev
        assert len(result["distribution"]) == 5

    def test_distribution_with_dict_list(self):
        """Test distribution calculation with list of dicts containing 'score' field."""
        scores = [
            {"score": 1.0, "name": "a"},
            {"score": 2.0, "name": "b"},
            {"score": 3.0, "name": "c"},
        ]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 2.0
        assert result["count"] == 3
        assert result["min_score"] == 1.0
        assert result["max_score"] == 3.0

    def test_z_scores_calculation(self):
        """Test that z-scores are calculated correctly."""
        # Mean = 3, std_dev ≈ 1.414
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_score_distribution(scores)

        # Find the middle value (3.0) - it should have z-score close to 0
        middle_dist = [d for d in result["distribution"] if d["score"] == 3.0][0]
        assert abs(middle_dist["z_score"]) < 0.01

        # Values below mean (1.0, 2.0) should have negative z-scores
        for d in result["distribution"]:
            if d["score"] < 3.0:
                assert d["z_score"] < 0

        # Values above mean (4.0, 5.0) should have positive z-scores
        for d in result["distribution"]:
            if d["score"] > 3.0:
                assert d["z_score"] > 0

    def test_percentile_calculation(self):
        """Test that percentiles are calculated correctly."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_score_distribution(scores)

        # Find lowest score (1.0) - should be 0th percentile (0% below it)
        lowest = [d for d in result["distribution"] if d["score"] == 1.0][0]
        assert lowest["percentile"] == 0.0

        # Find highest score (5.0) - should be 80th percentile (4 out of 5 below it)
        highest = [d for d in result["distribution"] if d["score"] == 5.0][0]
        assert highest["percentile"] == 80.0

    def test_normalized_scores(self):
        """Test that normalized scores are in 0-1 range."""
        scores = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calculate_score_distribution(scores)

        # Find min score (10.0) - should normalize to 0.0
        min_dist = [d for d in result["distribution"] if d["score"] == 10.0][0]
        assert min_dist["normalized"] == 0.0

        # Find max score (50.0) - should normalize to 1.0
        max_dist = [d for d in result["distribution"] if d["score"] == 50.0][0]
        assert max_dist["normalized"] == 1.0

        # Find middle score (30.0) - should be around 0.5
        middle_dist = [d for d in result["distribution"] if d["score"] == 30.0][0]
        assert abs(middle_dist["normalized"] - 0.5) < 0.01

        # All normalized scores should be between 0 and 1
        for dist in result["distribution"]:
            assert 0.0 <= dist["normalized"] <= 1.0

    def test_single_score(self):
        """Test distribution with a single score."""
        scores = [5.0]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 5.0
        assert result["std_dev"] == 0.0
        assert result["min_score"] == 5.0
        assert result["max_score"] == 5.0
        assert result["count"] == 1

        dist = result["distribution"][0]
        assert dist["score"] == 5.0
        assert dist["z_score"] == 0.0
        assert dist["percentile"] == 50.0  # Single/identical scores get median percentile
        assert dist["normalized"] == 1.0  # Single value normalizes to 1.0

    def test_identical_scores(self):
        """Test distribution when all scores are identical."""
        scores = [3.0, 3.0, 3.0, 3.0]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 3.0
        assert result["std_dev"] == 0.0
        assert result["min_score"] == 3.0
        assert result["max_score"] == 3.0

        # All z-scores should be 0 (no variance)
        # For identical scores, z-score is 0, percentile is 50, and normalized is 0.5
        for dist in result["distribution"]:
            assert dist["z_score"] == 0.0
            assert dist["percentile"] == 50.0
            assert dist["normalized"] == 0.5

    def test_empty_list(self):
        """Test distribution with empty list."""
        scores: list[float] = []
        result = calculate_score_distribution(scores)

        assert result["mean"] == 0.0
        assert result["std_dev"] == 0.0
        assert result["min_score"] == 0.0
        assert result["max_score"] == 0.0
        assert result["count"] == 0
        assert result["distribution"] == []

    def test_two_scores(self):
        """Test distribution with exactly two scores."""
        scores = [10.0, 20.0]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 15.0
        assert result["std_dev"] > 0
        assert result["min_score"] == 10.0
        assert result["max_score"] == 20.0
        assert result["count"] == 2

        # Find score 10.0 - should normalize to 0.0
        low_score = [d for d in result["distribution"] if d["score"] == 10.0][0]
        assert low_score["normalized"] == 0.0

        # Find score 20.0 - should normalize to 1.0
        high_score = [d for d in result["distribution"] if d["score"] == 20.0][0]
        assert high_score["normalized"] == 1.0

    def test_negative_scores(self):
        """Test distribution with negative scores."""
        scores = [-5.0, -3.0, 0.0, 3.0, 5.0]
        result = calculate_score_distribution(scores)

        assert result["mean"] == 0.0
        assert result["min_score"] == -5.0
        assert result["max_score"] == 5.0
        assert result["count"] == 5

        # Should still calculate valid distribution metrics
        assert len(result["distribution"]) == 5
        for dist in result["distribution"]:
            assert "z_score" in dist
            assert "percentile" in dist
            assert "normalized" in dist

    def test_large_range_scores(self):
        """Test distribution with large range of scores."""
        scores = [0.001, 0.01, 100.0, 1000.0]
        result = calculate_score_distribution(scores)

        assert result["count"] == 4
        assert result["min_score"] == 0.001
        assert result["max_score"] == 1000.0
        assert result["mean"] > 0

        # Distribution should handle large ranges
        assert len(result["distribution"]) == 4

    def test_decimal_precision(self):
        """Test that results are properly rounded."""
        scores = [1.23456789, 2.34567890, 3.45678901]
        result = calculate_score_distribution(scores)

        # Mean should be rounded to 4 decimal places
        assert isinstance(result["mean"], float)
        assert len(str(result["mean"]).split(".")[-1]) <= 4

        # All distribution values should be rounded
        for dist in result["distribution"]:
            assert len(str(dist["z_score"]).split(".")[-1]) <= 4
            assert len(str(dist["percentile"]).split(".")[-1]) <= 2
            assert len(str(dist["normalized"]).split(".")[-1]) <= 4

    def test_real_world_search_scores(self):
        """Test with realistic search result scores."""
        search_results = [
            {"score": 12.5, "name": "result1"},
            {"score": 8.3, "name": "result2"},
            {"score": 15.7, "name": "result3"},
            {"score": 6.2, "name": "result4"},
            {"score": 10.1, "name": "result5"},
        ]
        result = calculate_score_distribution(search_results)

        assert result["count"] == 5
        assert result["mean"] > 0
        assert result["std_dev"] > 0
        assert len(result["distribution"]) == 5

        # All metrics should be present for each score
        for dist in result["distribution"]:
            assert "score" in dist
            assert "z_score" in dist
            assert "percentile" in dist
            assert "normalized" in dist

    def test_distribution_sorted_by_z_score(self):
        """Test that distribution results are sorted by z-score (descending)."""
        scores = [10.0, 20.0, 5.0, 50.0, 15.0]
        result = calculate_score_distribution(scores)

        # Extract z-scores from distribution
        z_scores = [d["z_score"] for d in result["distribution"]]

        # Verify they're in descending order
        assert z_scores == sorted(z_scores, reverse=True)

        # Highest z-score (50.0) should be first
        assert result["distribution"][0]["score"] == 50.0
        assert result["distribution"][0]["z_score"] > 0

        # Lowest z-score (5.0) should be last
        assert result["distribution"][-1]["score"] == 5.0
        assert result["distribution"][-1]["z_score"] < 0


class TestGradeByZScore:
    """Tests for grade_by_z_score function."""

    def test_exceptional_tier(self):
        """Test z-scores in exceptional range (> 2.0)."""
        result = grade_by_z_score(2.5)
        assert result["tier"] == "exceptional"
        assert result["label"] == "Exceptional"
        assert result["rank"] == 1
        assert "Top ~2%" in result["description"]

        # Edge case: exactly 2.0 should be highly_relevant
        result_edge = grade_by_z_score(2.0)
        assert result_edge["tier"] == "highly_relevant"

    def test_highly_relevant_tier(self):
        """Test z-scores in highly relevant range (1.0 < z ≤ 2.0)."""
        result = grade_by_z_score(1.5)
        assert result["tier"] == "highly_relevant"
        assert result["label"] == "Highly Relevant"
        assert result["rank"] == 2
        assert "Top ~16%" in result["description"]

        # Test boundary at 1.01
        result_upper = grade_by_z_score(1.01)
        assert result_upper["tier"] == "highly_relevant"

        # Test boundary at 1.99
        result_lower = grade_by_z_score(1.99)
        assert result_lower["tier"] == "highly_relevant"

    def test_above_average_tier(self):
        """Test z-scores in above average range (0.0 < z ≤ 1.0)."""
        result = grade_by_z_score(0.5)
        assert result["tier"] == "above_average"
        assert result["label"] == "Above Average"
        assert result["rank"] == 3
        assert "Top 50%" in result["description"]

        # Edge case: exactly 1.0 should be above_average
        result_edge = grade_by_z_score(1.0)
        assert result_edge["tier"] == "above_average"

    def test_below_average_tier(self):
        """Test z-scores in below average range (-1.0 < z < 0.0)."""
        result = grade_by_z_score(-0.5)
        assert result["tier"] == "below_average"
        assert result["label"] == "Below Average"
        assert result["rank"] == 4
        assert "Bottom 50%" in result["description"]

        # Edge case: close to 0 but negative is still below_average
        result_edge = grade_by_z_score(-0.01)
        assert result_edge["tier"] == "below_average"
        assert result_edge["label"] == "Below Average"
        assert result_edge["rank"] == 4
        assert "Bottom 50%" in result_edge["description"]

    def test_poor_tier(self):
        """Test z-scores in poor range (≤ -1.0)."""
        result = grade_by_z_score(-2.0)
        assert result["tier"] == "poor"
        assert result["label"] == "Poor"
        assert result["rank"] == 5
        assert "Bottom ~16%" in result["description"]

        # Edge case: exactly -1.0 should be poor
        result_edge = grade_by_z_score(-1.0)
        assert result_edge["tier"] == "poor"

    def test_zero_z_score(self):
        """Test z-score of exactly 0 (mean)."""
        result = grade_by_z_score(0.0)
        assert result["tier"] == "above_average"  # At the mean = average, not below
        assert result["rank"] == 3

    def test_extreme_z_scores(self):
        """Test very large and very small z-scores."""
        # Very high z-score
        result_high = grade_by_z_score(5.0)
        assert result_high["tier"] == "exceptional"

        # Very low z-score
        result_low = grade_by_z_score(-5.0)
        assert result_low["tier"] == "poor"


class TestCalculateScoreDistributionWithTiers:
    """Tests for calculate_score_distribution_with_tiers function."""

    def test_basic_distribution_with_tiers(self):
        """Test that tiers are added to each distribution entry."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Should have all the same base fields
        assert "mean" in result
        assert "std_dev" in result
        assert "distribution" in result

        # Each distribution entry should have tier info
        for dist in result["distribution"]:
            assert "score" in dist
            assert "z_score" in dist
            assert "tier" in dist
            assert "tier_label" in dist
            assert "tier_description" in dist
            assert "tier_rank" in dist

    def test_tiers_sorted_by_z_score(self):
        """Test that results are sorted by z-score with appropriate tiers."""
        scores = [1.0, 5.0, 10.0, 15.0, 100.0]
        result = calculate_score_distribution_with_tiers(scores)

        # First result should have highest z-score
        first = result["distribution"][0]
        assert first["score"] == 100.0
        assert first["tier_rank"] <= 3  # Should be in top 3 tiers

        # Last result should have lowest z-score
        last = result["distribution"][-1]
        assert last["score"] == 1.0
        assert last["tier_rank"] >= 3  # Should be in bottom tiers

    def test_tier_consistency(self):
        """Test that tier assignments are consistent with z-scores."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = calculate_score_distribution_with_tiers(scores)

        for dist in result["distribution"]:
            z = dist["z_score"]
            tier = dist["tier"]

            # Verify tier matches z-score thresholds
            if z > 2.0:
                assert tier == "exceptional"
            elif z > 1.0:
                assert tier == "highly_relevant"
            elif z > 0.0:
                assert tier == "above_average"
            elif z > -1.0:
                assert tier == "below_average"
            else:
                assert tier == "poor"

    def test_with_dict_list(self):
        """Test tiers with list of dicts (search results)."""
        search_results = [
            {"score": 5.0, "name": "low"},
            {"score": 15.0, "name": "medium"},
            {"score": 50.0, "name": "high"},
        ]
        result = calculate_score_distribution_with_tiers(search_results)

        assert len(result["distribution"]) == 3

        # All entries should have tier info
        for dist in result["distribution"]:
            assert "tier" in dist
            assert "tier_rank" in dist

    def test_empty_list_with_tiers(self):
        """Test with empty list."""
        scores: list[float] = []
        result = calculate_score_distribution_with_tiers(scores)

        assert result["count"] == 0
        assert result["distribution"] == []

    def test_single_score_with_tier(self):
        """Test with single score."""
        scores = [10.0]
        result = calculate_score_distribution_with_tiers(scores)

        assert len(result["distribution"]) == 1
        dist = result["distribution"][0]

        # Single score has z-score of 0
        assert dist["z_score"] == 0.0
        assert dist["tier"] == "above_average"  # z=0 is at the mean = above_average tier

    def test_tier_rank_ordering(self):
        """Test that tier_rank values are in correct order (1 is best)."""
        scores = list(range(1, 11))  # [1, 2, 3, ... 10]
        result = calculate_score_distribution_with_tiers(scores)

        # Ranks should be monotonically non-decreasing (since sorted by z-score desc)
        ranks = [d["tier_rank"] for d in result["distribution"]]
        for i in range(len(ranks) - 1):
            assert ranks[i] <= ranks[i + 1], "Ranks should be non-decreasing"


class TestFilterByRelevanceTier:
    """Tests for filter_by_relevance_tier function."""

    def test_filter_by_min_tier_rank(self):
        """Test filtering by minimum tier rank."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for top 2 tiers (exceptional + highly_relevant)
        top_tier = filter_by_relevance_tier(result["distribution"], min_tier_rank=2)

        # All results should have tier_rank <= 2
        for entry in top_tier:
            assert entry["tier_rank"] <= 2

        # Should have at least some results
        assert len(top_tier) > 0
        assert len(top_tier) <= len(result["distribution"])

    def test_filter_by_tier_names(self):
        """Test filtering by specific tier names."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for exceptional only
        exceptional = filter_by_relevance_tier(result["distribution"], tier_names=["exceptional"])

        # All results should be exceptional tier
        for entry in exceptional:
            assert entry["tier"] == "exceptional"

    def test_filter_by_multiple_tier_names(self):
        """Test filtering by multiple tier names."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for exceptional OR highly_relevant
        top_tiers = filter_by_relevance_tier(
            result["distribution"], tier_names=["exceptional", "highly_relevant"]
        )

        # All results should be in one of these tiers
        for entry in top_tiers:
            assert entry["tier"] in ["exceptional", "highly_relevant"]

    def test_filter_combined_or_logic(self):
        """Test that min_tier_rank and tier_names use OR logic."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter: rank <= 1 OR tier in ['highly_relevant']
        # Should include exceptional (rank 1) + highly_relevant (rank 2)
        filtered = filter_by_relevance_tier(
            result["distribution"], min_tier_rank=1, tier_names=["highly_relevant"]
        )

        # Should include both tiers
        tiers = {entry["tier"] for entry in filtered}
        assert "exceptional" in tiers or "highly_relevant" in tiers

    def test_filter_empty_distribution(self):
        """Test filtering empty distribution."""
        empty_dist: list[dict] = []
        result = filter_by_relevance_tier(empty_dist, min_tier_rank=2)
        assert result == []

    def test_filter_no_filters_returns_all(self):
        """Test that no filters returns all results."""
        scores = [1.0, 5.0, 10.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Call with no filters
        all_results = filter_by_relevance_tier(result["distribution"])

        assert len(all_results) == len(result["distribution"])

    def test_filter_maintains_sort_order(self):
        """Test that filtering maintains z-score sort order."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for top 3 tiers
        filtered = filter_by_relevance_tier(result["distribution"], min_tier_rank=3)

        # Z-scores should still be in descending order
        z_scores = [entry["z_score"] for entry in filtered]
        assert z_scores == sorted(z_scores, reverse=True)

    def test_filter_rank_1_only_exceptional(self):
        """Test that rank 1 filter returns only exceptional results."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for rank 1 only
        rank_1 = filter_by_relevance_tier(result["distribution"], min_tier_rank=1)

        # All should be exceptional
        for entry in rank_1:
            assert entry["tier"] == "exceptional"
            assert entry["tier_rank"] == 1

    def test_filter_rank_3_includes_top_three(self):
        """Test that rank 3 filter includes top 3 tiers."""
        scores = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Filter for rank <= 3
        top_3 = filter_by_relevance_tier(result["distribution"], min_tier_rank=3)

        # Should only have ranks 1, 2, or 3
        for entry in top_3:
            assert entry["tier_rank"] <= 3
            assert entry["tier"] in ["exceptional", "highly_relevant", "above_average"]

    def test_filter_with_real_search_results(self):
        """Test filtering with realistic search result scores."""
        search_results = [
            {"score": 2.5, "name": "weak"},
            {"score": 5.0, "name": "poor"},
            {"score": 10.0, "name": "below_avg"},
            {"score": 15.0, "name": "above_avg"},
            {"score": 25.0, "name": "good"},
            {"score": 50.0, "name": "exceptional"},
        ]
        result = calculate_score_distribution_with_tiers(search_results)

        # Filter for high quality only (rank <= 2)
        high_quality = filter_by_relevance_tier(result["distribution"], min_tier_rank=2)

        # Should have fewer results than original
        assert len(high_quality) < len(result["distribution"])

        # All should be high quality
        for entry in high_quality:
            assert entry["tier_rank"] <= 2

    def test_filter_tier_names_case_sensitive(self):
        """Test that tier name filtering is case-sensitive."""
        scores = [1.0, 10.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Try with wrong case - should return nothing
        wrong_case = filter_by_relevance_tier(
            result["distribution"], tier_names=["Exceptional"]  # Capital E
        )

        # Should be empty since tier names are lowercase
        assert len(wrong_case) == 0

    def test_filter_nonexistent_tier_name(self):
        """Test filtering with non-existent tier name."""
        scores = [1.0, 10.0, 50.0]
        result = calculate_score_distribution_with_tiers(scores)

        # Try with fake tier name
        fake_tier = filter_by_relevance_tier(
            result["distribution"], tier_names=["super_exceptional"]
        )

        # Should be empty
        assert len(fake_tier) == 0

    def test_filter_entries_without_tier_info(self):
        """Test filtering handles entries missing tier information."""
        # Create distribution with missing tier info
        incomplete_dist = [
            {"score": 10.0, "z_score": 0.5},  # Missing tier fields
            {
                "score": 20.0,
                "z_score": 1.5,
                "tier": "highly_relevant",
                "tier_rank": 2,
            },
        ]

        # Filter should skip entries without tier info
        filtered = filter_by_relevance_tier(incomplete_dist, min_tier_rank=2)

        # Should only include the complete entry
        assert len(filtered) == 1
        assert filtered[0]["score"] == 20.0
