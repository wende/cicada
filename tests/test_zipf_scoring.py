"""Tests for Zipf-based keyword scoring."""

import fnmatch

import pytest

from cicada.keyword_search import KeywordSearcher
from cicada.scoring import (
    EXACT_NAME_MATCH_SCORE,
    build_zipf_table,
    calculate_score,
    calculate_wildcard_score,
)


class TestBuildZipfTable:
    """Unit tests for build_zipf_table()."""

    def test_empty_documents(self):
        """Empty document list returns empty table."""
        assert build_zipf_table([]) == {}

    def test_single_doc_single_keyword(self):
        """Single doc with single keyword gets weight 1.0."""
        docs = [{"keywords": {"alpha": 0.5}}]
        table = build_zipf_table(docs)
        assert table == {"alpha": 1.0}

    def test_single_doc_multiple_keywords(self):
        """All keywords in one doc share rank 1 (same frequency)."""
        docs = [{"keywords": {"alpha": 0.5, "beta": 0.3, "gamma": 0.7}}]
        table = build_zipf_table(docs)
        assert table == {"alpha": 1.0, "beta": 1.0, "gamma": 1.0}

    def test_different_frequencies(self):
        """Keywords with different doc frequencies get different weights."""
        docs = [
            {"keywords": {"common": 1.0, "rare": 1.0}},
            {"keywords": {"common": 1.0}},
        ]
        table = build_zipf_table(docs)
        assert table["rare"] == 1.0  # freq 1 -> rank 1
        assert table["common"] == 0.5  # freq 2 -> rank 2

    def test_dense_ranking_ex_aequo(self):
        """Keywords with equal frequency share the same rank."""
        docs = [
            {"keywords": {"a": 1.0, "b": 1.0, "c": 1.0}},
            {"keywords": {"a": 1.0, "b": 1.0}},
            {"keywords": {"a": 1.0}},
        ]
        table = build_zipf_table(docs)
        # c: freq 1 -> rank 1 -> weight 1.0
        assert table["c"] == 1.0
        # b: freq 2 -> rank 2 -> weight 0.5
        assert table["b"] == 0.5
        # a: freq 3 -> rank 3 -> weight 1/3
        assert table["a"] == pytest.approx(1 / 3)

    def test_power_law_distribution(self):
        """Weights follow 1/rank power law."""
        docs = [
            {"keywords": {"k1": 1.0, "k2": 1.0, "k3": 1.0}},
            {"keywords": {"k2": 1.0, "k3": 1.0}},
            {"keywords": {"k3": 1.0}},
        ]
        table = build_zipf_table(docs)
        # k1: 1 doc -> rank 1 -> 1.0
        assert table["k1"] == 1.0
        # k2: 2 docs -> rank 2 -> 0.5
        assert table["k2"] == 0.5
        # k3: 3 docs -> rank 3 -> 1/3
        assert table["k3"] == pytest.approx(1 / 3)

    def test_keyword_counted_once_per_document(self):
        """Each keyword counted once per document regardless of weight value."""
        docs = [
            {"keywords": {"kw": 5.0}},
            {"keywords": {"kw": 0.1}},
        ]
        table = build_zipf_table(docs)
        # kw appears in 2 docs but it's the only keyword -> rank 1
        assert table["kw"] == 1.0


class TestZipfScoring:
    """Unit tests for calculate_score() with zipf_weights param."""

    def test_no_zipf_backward_compatible(self):
        """Without zipf_weights, scores are unchanged."""
        result = calculate_score(["alpha"], [0], 1, {"alpha": 1.0})
        # Base: 1.0, coverage 100% -> 1.6
        assert result["score"] == pytest.approx(1.6)

    def test_zipf_weight_one_no_change(self):
        """Zipf weight 1.0 produces same score as no Zipf."""
        result = calculate_score(
            ["alpha"],
            [0],
            1,
            {"alpha": 1.0},
            zipf_weights={"alpha": 1.0},
        )
        assert result["score"] == pytest.approx(1.6)

    def test_rare_vs_common_scoring(self):
        """Rare keyword (weight 1.0) scores 10x higher than common (weight 0.1)."""
        rare_result = calculate_score(
            ["rare"],
            [0],
            1,
            {"rare": 1.0},
            zipf_weights={"rare": 1.0},
        )
        common_result = calculate_score(
            ["common"],
            [0],
            1,
            {"common": 1.0},
            zipf_weights={"common": 0.1},
        )
        # rare: 1.0 * 1.0 * 1.6 = 1.6
        # common: 1.0 * 0.1 * 1.6 = 0.16
        assert rare_result["score"] / common_result["score"] == pytest.approx(10.0)

    def test_unknown_keyword_defaults_to_one(self):
        """Keywords not in zipf_weights default to weight 1.0."""
        result = calculate_score(
            ["unknown"],
            [0],
            1,
            {"unknown": 1.0},
            zipf_weights={},
        )
        # unknown defaults to 1.0: 1.0 * 1.0 = 1.0, coverage 1.6
        assert result["score"] == pytest.approx(1.6)

    def test_exact_name_match_not_affected(self):
        """EXACT_NAME_MATCH_SCORE is not multiplied by Zipf weight."""
        result = calculate_score(
            ["myfunction"],
            [0],
            1,
            {"other": 1.0},
            doc_name="Module.myfunction/1",
            zipf_weights={"myfunction": 0.1},
        )
        # Name match: EXACT_NAME_MATCH_SCORE = 3.0, coverage 1.6 -> 4.8
        assert result["score"] == pytest.approx(EXACT_NAME_MATCH_SCORE * 1.6)

    def test_mixed_rare_common_keywords(self):
        """Mixed rare/common keywords with correct math."""
        result = calculate_score(
            ["rare", "common"],
            [0, 1],
            2,
            {"rare": 1.0, "common": 1.0},
            zipf_weights={"rare": 1.0, "common": 0.5},
        )
        # rare: 1.0 * 1.0 * 1.0 = 1.0
        # common: 1.0 * 1.0 * 0.5 = 0.5
        # base: 1.5, coverage 2/2 = 100% -> 1.6x
        # final: 1.5 * 1.6 = 2.4
        assert result["score"] == pytest.approx(2.4)


class TestZipfWildcardScoring:
    """Wildcard scoring with Zipf."""

    def _match_wildcard(self, pattern, text):
        return fnmatch.fnmatch(text.lower(), pattern.lower())

    def test_wildcard_uses_doc_keyword_zipf_weight(self):
        """Wildcard match uses Zipf weight of the matched doc keyword."""
        result = calculate_wildcard_score(
            ["rar*"],
            [0],
            1,
            {"rare": 1.0},
            self._match_wildcard,
            zipf_weights={"rare": 0.5},
        )
        # rare matched by rar*: 1.0 * 1.0 * 0.5 = 0.5, coverage 1.6
        assert result["score"] == pytest.approx(0.5 * 1.6)

    def test_wildcard_name_match_not_affected(self):
        """Wildcard name match is not affected by Zipf."""
        result = calculate_wildcard_score(
            ["my*"],
            [0],
            1,
            {"other": 1.0},
            self._match_wildcard,
            doc_name="Module.myfunction/1",
            zipf_weights={"my*": 0.1},
        )
        # Name match: EXACT_NAME_MATCH_SCORE = 3.0, coverage 1.6 -> 4.8
        assert result["score"] == pytest.approx(EXACT_NAME_MATCH_SCORE * 1.6)

    def test_wildcard_uses_best_zipf_weighted_match_independent_of_order(self):
        """Wildcard score chooses the best weighted match, not first dict item."""
        query_keywords = ["a*"]
        keyword_groups = [0]
        zipf_weights = {"alpha": 0.2, "atom": 0.8}

        alpha_first = calculate_wildcard_score(
            query_keywords,
            keyword_groups,
            1,
            {"alpha": 1.0, "atom": 1.0},
            self._match_wildcard,
            zipf_weights=zipf_weights,
        )
        atom_first = calculate_wildcard_score(
            query_keywords,
            keyword_groups,
            1,
            {"atom": 1.0, "alpha": 1.0},
            self._match_wildcard,
            zipf_weights=zipf_weights,
        )

        # Best match is atom: 1.0 * 0.8 = 0.8, coverage 1.6 -> 1.28
        assert alpha_first["score"] == pytest.approx(1.28)
        assert atom_first["score"] == pytest.approx(1.28)


class TestZipfSearcherIntegration:
    """End-to-end through KeywordSearcher.search()."""

    @pytest.fixture
    def zipf_index(self):
        """Fixture with 'common' in all 3 modules, 'rare' in only 1."""
        return {
            "modules": {
                "ModuleA": {
                    "file": "a.py",
                    "line": 1,
                    "keywords": {"common": 1.0, "rare": 1.0, "alpha": 0.8},
                    "functions": [],
                },
                "ModuleB": {
                    "file": "b.py",
                    "line": 1,
                    "keywords": {"common": 1.0, "beta": 0.8},
                    "functions": [],
                },
                "ModuleC": {
                    "file": "c.py",
                    "line": 1,
                    "keywords": {"common": 1.0, "gamma": 0.8},
                    "functions": [],
                },
            }
        }

    def test_rare_keyword_boosts_right_result(self, zipf_index):
        """Searching for 'rare' should only match ModuleA."""
        searcher = KeywordSearcher(zipf_index)
        results = searcher.search(["rare"], top_n=10)
        assert len(results) == 1
        assert results[0]["name"] == "ModuleA"

    def test_common_keyword_scores_lower(self, zipf_index):
        """Common keyword should score lower than rare for the same module."""
        searcher = KeywordSearcher(zipf_index)
        rare_results = searcher.search(["rare"], top_n=10)
        common_results = searcher.search(["common"], top_n=10)

        rare_score = next(r["score"] for r in rare_results if r["name"] == "ModuleA")
        common_score = next(r["score"] for r in common_results if r["name"] == "ModuleA")

        assert rare_score > common_score

    def test_zipf_table_populated(self, zipf_index):
        """The zipf_table attribute should be populated with correct weights."""
        searcher = KeywordSearcher(zipf_index)
        # 'common' appears in 3 docs -> highest freq -> lowest weight
        # 'rare' appears in 1 doc -> lowest freq -> highest weight
        assert searcher.zipf_table["rare"] > searcher.zipf_table["common"]
        assert searcher.zipf_table["rare"] == 1.0
        # alpha, beta, gamma all appear in 1 doc each -> same weight as rare
        assert searcher.zipf_table["alpha"] == 1.0
        assert searcher.zipf_table["beta"] == 1.0
        assert searcher.zipf_table["gamma"] == 1.0
