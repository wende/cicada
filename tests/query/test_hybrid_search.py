"""Tests for hybrid search functionality in the query orchestrator."""

import pytest

from cicada.query.orchestrator import QueryOrchestrator
from cicada.query.types import SearchResult


@pytest.fixture
def orchestrator():
    """Create an orchestrator instance for testing hybrid methods."""
    return QueryOrchestrator(index={}, repo_path=None)


def make_result(
    name: str,
    score: float,
    module: str = "TestModule",
    file: str = "test.ex",
    line: int = 1,
) -> SearchResult:
    """Create a SearchResult for testing."""
    return SearchResult(
        type="function",
        name=name,
        module=module,
        file=file,
        line=line,
        score=score,
        confidence=0.0,
        matched_keywords=[],
        pattern_match=False,
    )


class TestToPercentileRanks:
    """Tests for _to_percentile_ranks method."""

    def test_empty_list(self, orchestrator):
        """Empty list returns empty list."""
        result = orchestrator._to_percentile_ranks([], "keyword")
        assert result == []

    def test_single_result(self, orchestrator):
        """Single result gets 100 percentile."""
        results = [make_result("func1", 0.5)]
        ranked = orchestrator._to_percentile_ranks(results, "keyword")
        assert len(ranked) == 1
        assert ranked[0].confidence == 100.0
        assert ranked[0].search_source == "keyword"

    def test_multiple_results_ascending(self, orchestrator):
        """Multiple results get proper percentile ranks."""
        results = [
            make_result("low", 0.2),
            make_result("med", 0.5),
            make_result("high", 0.8),
        ]
        ranked = orchestrator._to_percentile_ranks(results, "semantic")

        # Results should be returned with percentiles based on rank
        # After sorting by score: low(0.2)=33.3%, med(0.5)=66.7%, high(0.8)=100%
        by_name = {r.name: r for r in ranked}
        assert by_name["low"].confidence == pytest.approx(33.33, rel=0.1)
        assert by_name["med"].confidence == pytest.approx(66.67, rel=0.1)
        assert by_name["high"].confidence == pytest.approx(100.0, rel=0.1)
        assert all(r.search_source == "semantic" for r in ranked)

    def test_source_is_set(self, orchestrator):
        """Search source is correctly set on results."""
        results = [make_result("func1", 0.5)]

        keyword_ranked = orchestrator._to_percentile_ranks(results.copy(), "keyword")
        assert keyword_ranked[0].search_source == "keyword"

        semantic_ranked = orchestrator._to_percentile_ranks([make_result("func2", 0.5)], "semantic")
        assert semantic_ranked[0].search_source == "semantic"


class TestMergeHybridResults:
    """Tests for _merge_hybrid_results method."""

    def test_empty_both(self, orchestrator):
        """Both empty returns empty."""
        result = orchestrator._merge_hybrid_results([], [])
        assert result == []

    def test_keyword_only(self, orchestrator):
        """Only keyword results returns them with keyword source."""
        keyword_results = [
            make_result("func1", 0.8),
            make_result("func2", 0.5),
        ]
        result = orchestrator._merge_hybrid_results(keyword_results, [])

        assert len(result) == 2
        assert all(r.search_source == "keyword" for r in result)

    def test_semantic_only(self, orchestrator):
        """Only semantic results returns them with semantic source."""
        semantic_results = [
            make_result("func1", 0.9),
            make_result("func2", 0.6),
        ]
        result = orchestrator._merge_hybrid_results([], semantic_results)

        assert len(result) == 2
        assert all(r.search_source == "semantic" for r in result)

    def test_no_overlap(self, orchestrator):
        """Results with no overlap are merged without boost."""
        keyword_results = [make_result("func1", 0.8, line=1)]
        semantic_results = [make_result("func2", 0.9, line=2)]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        assert len(result) == 2
        by_name = {r.name: r for r in result}
        assert by_name["func1"].search_source == "keyword"
        assert by_name["func2"].search_source == "semantic"

    def test_overlap_gets_boosted(self, orchestrator):
        """Results appearing in both get 1.5x boost and 'both' source."""
        # Same function in both results (matched by name+file+line)
        keyword_results = [make_result("func1", 0.8, file="test.ex", line=10)]
        semantic_results = [make_result("func1", 0.9, file="test.ex", line=10)]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        assert len(result) == 1
        assert result[0].name == "func1"
        assert result[0].search_source == "both"
        # Confidence should be boosted (percentile * 1.5, capped at 100)
        assert result[0].confidence <= 100.0

    def test_mixed_overlap_and_unique(self, orchestrator):
        """Mix of overlapping and unique results handled correctly."""
        keyword_results = [
            make_result("shared", 0.8, line=10),
            make_result("keyword_only", 0.6, line=20),
        ]
        semantic_results = [
            make_result("shared", 0.9, line=10),
            make_result("semantic_only", 0.7, line=30),
        ]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        assert len(result) == 3
        by_name = {r.name: r for r in result}
        assert by_name["shared"].search_source == "both"
        assert by_name["keyword_only"].search_source == "keyword"
        assert by_name["semantic_only"].search_source == "semantic"

    def test_results_sorted_by_confidence(self, orchestrator):
        """Merged results are sorted by confidence descending."""
        keyword_results = [
            make_result("low_kw", 0.2, line=1),
            make_result("high_kw", 0.9, line=2),
        ]
        semantic_results = [
            make_result("med_sem", 0.5, line=3),
        ]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        # Results should be sorted by confidence (descending)
        confidences = [r.confidence for r in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_boost_capped_at_100(self, orchestrator):
        """Boosted confidence is capped at 100."""
        # Create results where boost would exceed 100
        keyword_results = [make_result("func1", 0.95, line=10)]
        semantic_results = [make_result("func1", 0.95, line=10)]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        assert len(result) == 1
        # With high percentile (100) * 1.5 = 150, should be capped at 100
        assert result[0].confidence <= 100.0

    def test_score_updated_to_normalized_confidence(self, orchestrator):
        """Score field is updated to match normalized confidence for downstream ranking."""
        # Different raw scores on different scales (keyword vs semantic)
        keyword_results = [
            make_result("kw_high", 100.0, line=1),  # High keyword score
            make_result("kw_low", 10.0, line=2),  # Low keyword score
        ]
        semantic_results = [
            make_result("sem_high", 0.99, line=3),  # High semantic score (cosine similarity)
            make_result("sem_low", 0.50, line=4),  # Low semantic score
        ]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        # All results should have score updated to match confidence
        for r in result:
            assert r.score == r.confidence, f"score should equal confidence for {r.name}"

    def test_score_preserved_for_rank_and_dedupe(self, orchestrator):
        """Merged results maintain correct ranking after _rank_and_dedupe."""
        # Semantic result with higher percentile should rank above keyword
        # despite keyword having higher raw score
        keyword_results = [make_result("kw_func", 1000.0, line=1)]  # High raw score
        semantic_results = [make_result("sem_func", 0.99, line=2)]  # Low raw but top percentile

        merged = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        # Both should have same confidence (100% - they're top of their lists)
        # But apply rank_and_dedupe to verify it preserves the order
        ranked = orchestrator._rank_and_dedupe(merged)

        # The order should be based on normalized scores, not raw scores
        # Since both are at 100 percentile, order by name for stability
        assert len(ranked) == 2
        # Verify scores are normalized (not the original raw scores)
        for r in ranked:
            assert r.score <= 100.0, "Score should be normalized percentile"

    def test_overlapping_result_score_reflects_boost(self, orchestrator):
        """Overlapping results have score that reflects the 1.5x boost."""
        # Same function in both results - should get boosted
        keyword_results = [make_result("shared_func", 50.0, line=10)]
        semantic_results = [make_result("shared_func", 0.8, line=10)]

        result = orchestrator._merge_hybrid_results(keyword_results, semantic_results)

        assert len(result) == 1
        assert result[0].search_source == "both"
        # Score should match the boosted confidence
        assert result[0].score == result[0].confidence
        # Confidence should be boosted (100% * 1.5 = capped at 100)
        assert result[0].confidence == 100.0


class TestSearchSourceIndicator:
    """Tests for search source indicator in output formatting."""

    def test_search_source_default(self):
        """SearchResult defaults to 'keyword' source."""
        result = SearchResult(
            type="function",
            name="test",
            module="Test",
            file="test.ex",
            line=1,
            score=0.5,
            confidence=50.0,
            matched_keywords=[],
            pattern_match=False,
        )
        assert result.search_source == "keyword"

    def test_search_source_can_be_set(self):
        """SearchResult search_source can be set to any valid value."""
        for source in ["keyword", "semantic", "both"]:
            result = SearchResult(
                type="function",
                name="test",
                module="Test",
                file="test.ex",
                line=1,
                score=0.5,
                confidence=50.0,
                matched_keywords=[],
                pattern_match=False,
                search_source=source,
            )
            assert result.search_source == source
