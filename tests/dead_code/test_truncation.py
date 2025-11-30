"""Tests for truncation feature in dead code finder.

Tests the new truncation functionality that limits output to max_results_per_tier
per confidence level to prevent overwhelming output.
"""

import pytest

from cicada.dead_code.finder import format_markdown


@pytest.fixture
def results_with_many_high():
    """Results with 75 high confidence candidates (should trigger truncation)."""
    candidates = []
    for i in range(75):
        candidates.append(
            {
                "module": f"MyApp.Module{i // 3}",  # Group every 3 into same module
                "function": f"unused_func_{i}",
                "arity": 1,
                "line": 10 + i,
                "file": f"lib/my_app/module{i // 3}.ex",
                "reason": "Zero usage found",
            }
        )
    return {
        "summary": {
            "total_public_functions": 100,
            "analyzed": 100,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": 75,
        },
        "candidates": {"high": candidates, "medium": [], "low": []},
    }


@pytest.fixture
def results_with_exactly_fifty():
    """Results with exactly 50 high confidence candidates (no truncation)."""
    candidates = []
    for i in range(50):
        candidates.append(
            {
                "module": "MyApp.Module",
                "function": f"unused_func_{i}",
                "arity": 1,
                "line": 10 + i,
                "file": "lib/my_app/module.ex",
                "reason": "Zero usage found",
            }
        )
    return {
        "summary": {
            "total_public_functions": 100,
            "analyzed": 100,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": 50,
        },
        "candidates": {"high": candidates, "medium": [], "low": []},
    }


@pytest.fixture
def empty_results():
    """Results with no candidates."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 0,
        },
        "candidates": {"high": [], "medium": [], "low": []},
    }


def test_format_markdown_truncates_at_limit(results_with_many_high):
    """Test that markdown output truncates results when exceeding max_results_per_tier."""
    output = format_markdown(results_with_many_high, max_results_per_tier=50)

    # Should show truncation message
    assert "and 25 more high confidence candidates (truncated for readability)" in output
    assert "Tip: Use JSON format or filter results for complete output" in output

    # Should mention total count in header
    assert "75 functions" in output


def test_format_markdown_no_truncation_at_limit(results_with_exactly_fifty):
    """Test that markdown output does not truncate when exactly at limit."""
    output = format_markdown(results_with_exactly_fifty, max_results_per_tier=50)

    # Should NOT show truncation message
    assert "more high confidence candidates" not in output
    assert "truncated for readability" not in output


def test_format_markdown_custom_truncation_limit(results_with_many_high):
    """Test that custom truncation limit works correctly."""
    output = format_markdown(results_with_many_high, max_results_per_tier=10)

    # Should show different truncation count
    assert "and 65 more high confidence candidates (truncated for readability)" in output


def test_format_markdown_truncation_all_tiers():
    """Test truncation works for all three tiers independently."""
    # Create results with > 50 in each tier
    candidates_per_tier = 60
    results = {
        "summary": {
            "total_public_functions": 200,
            "analyzed": 200,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": candidates_per_tier * 3,
        },
        "candidates": {
            "high": [
                {
                    "module": "MyApp.HighModule",
                    "function": f"unused_{i}",
                    "arity": 0,
                    "line": i,
                    "file": "lib/high.ex",
                    "reason": "Zero usage",
                }
                for i in range(candidates_per_tier)
            ],
            "medium": [
                {
                    "module": "MyApp.MediumModule",
                    "function": f"unused_{i}",
                    "arity": 0,
                    "line": i,
                    "file": "lib/medium.ex",
                    "reason": "Zero usage",
                    "behaviours": ["GenServer"],
                }
                for i in range(candidates_per_tier)
            ],
            "low": [
                {
                    "module": "MyApp.LowModule",
                    "function": f"unused_{i}",
                    "arity": 0,
                    "line": i,
                    "file": "lib/low.ex",
                    "reason": "Zero usage",
                    "mentioned_in": [{"module": "Other", "file": "other.ex"}],
                }
                for i in range(candidates_per_tier)
            ],
        },
    }

    output = format_markdown(results, max_results_per_tier=50)

    # Should show truncation for all three tiers
    assert "and 10 more high confidence candidates" in output
    assert "and 10 more medium confidence candidates" in output
    assert "and 10 more low confidence candidates" in output


def test_format_markdown_zero_results_no_truncation(empty_results):
    """Test that empty results don't show truncation messages."""
    output = format_markdown(empty_results)

    assert "truncated" not in output
    assert "*No dead code candidates found!*" in output


def test_format_markdown_truncation_edge_case_one_over():
    """Test truncation with exactly one more than limit (edge case)."""
    results = {
        "summary": {
            "total_public_functions": 51,
            "analyzed": 51,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": 51,
        },
        "candidates": {
            "high": [
                {
                    "module": "MyApp.Module",
                    "function": f"unused_{i}",
                    "arity": 0,
                    "line": i,
                    "file": "lib/module.ex",
                    "reason": "Zero usage",
                }
                for i in range(51)
            ],
            "medium": [],
            "low": [],
        },
    }

    output = format_markdown(results, max_results_per_tier=50)

    # Should show truncation for exactly 1 remaining
    assert "and 1 more high confidence candidate (truncated for readability)" in output
    # Note: singular "candidate" not "candidates"
