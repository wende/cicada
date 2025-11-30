"""
Score calculation logic for keyword search.

Provides functions to calculate search scores by summing weights of matched keywords,
with support for wildcard pattern matching and module name boosting.
"""

import math
from collections import defaultdict
from collections.abc import Callable
from typing import Any

# Normalization constants for score distribution
# When all scores are identical, normalize to midpoint (no variance to distinguish)
NORMALIZED_NO_VARIANCE = 0.5
# When there's only one score, treat it as maximum (100% of available values)
NORMALIZED_SINGLE_VALUE = 1.0

# Standard normal distribution significance thresholds (in standard deviations σ)
# These thresholds are based on statistical significance levels
Z_SCORE_EXCEPTIONAL_THRESHOLD = 2.0  # 97.7th percentile (>2σ above mean)
Z_SCORE_HIGHLY_RELEVANT_THRESHOLD = 1.0  # 84th percentile (1-2σ above mean)
Z_SCORE_MEAN_THRESHOLD = 0.0  # 50th percentile (at the mean)
Z_SCORE_POOR_THRESHOLD = -1.0  # 16th percentile (>1σ below mean)

# Module match boost value
MODULE_MATCH_BOOST = 2.0

# Diminishing returns factor for repeated keyword matches
DIMINISHING_RETURNS_FACTOR = 0.5

# Coverage bonus constants
COVERAGE_BONUS_BASE = 0.8
COVERAGE_BONUS_SCALE = 0.8

# Exact name match score (for function/module name matches)
# This is a high score awarded when a query keyword exactly matches the function/module name
# (e.g., searching for "__init__" matches the __init__ function)
EXACT_NAME_MATCH_SCORE = 3.0


def _extract_simple_name(doc_name: str | None) -> str | None:
    """
    Extract the simple function/module name from a qualified name.

    Handles qualified names with optional arity suffix:
    - "MyApp.User.create_user/2" -> "create_user"
    - "MyApp.User.__init__/1" -> "__init__"
    - "create_user/2" -> "create_user"
    - "MyApp.User" -> "user"

    Note: The result is lowercased for case-insensitive matching.

    Args:
        doc_name: Qualified name, optionally with /N arity suffix

    Returns:
        Lowercased simple name (last part after dots), or None if doc_name is None
    """
    if not doc_name:
        return None
    # Remove arity suffix first (/N)
    name_without_arity = doc_name.split("/")[0]
    # Then get the last part after dots
    return name_without_arity.split(".")[-1].lower()


def _build_score_result(
    total_score: float,
    matched_keywords: list[str],
    matched_groups: set[int],
    total_terms: int,
    query_keywords: list[str],
) -> dict[str, Any]:
    """
    Build the score result dictionary with confidence calculation.

    Args:
        total_score: Sum of matched keyword weights
        matched_keywords: List of matched keywords
        matched_groups: Set of matched group indexes
        total_terms: Total number of original query terms
        query_keywords: Full list of query keywords

    Returns:
        Dictionary with score, matched_keywords, and confidence
    """
    denominator = total_terms if total_terms else len(query_keywords)
    confidence = (len(matched_groups) / denominator * 100) if denominator else 0

    return {
        "score": total_score,
        "matched_keywords": matched_keywords,
        "confidence": round(confidence, 1),
    }


def _apply_coverage_bonus(
    base_score: float,
    matched_groups: set[int],
    total_terms: int,
    query_keywords: list[str],
) -> float:
    """Apply coverage multiplier to the base score.

    Coverage is computed using the original term groups so OR synonyms don't
    reduce coverage. When no terms match, short-circuit to return zero.
    """
    if not matched_groups or base_score == 0.0:
        return 0.0

    denominator = total_terms if total_terms else len(set(query_keywords))
    coverage_ratio = len(matched_groups) / denominator if denominator else 0

    # Coverage multiplier scales from 0.8x to 1.6x
    coverage_multiplier = COVERAGE_BONUS_BASE + (coverage_ratio * COVERAGE_BONUS_SCALE)
    return base_score * coverage_multiplier


def calculate_score(
    query_keywords: list[str],
    keyword_groups: list[int],
    total_terms: int,
    doc_keywords: dict[str, float],
    doc_name: str | None = None,
) -> dict[str, Any]:
    """
    Calculate search score with hybrid scoring (diminishing returns + coverage bonus).

    Scoring formula:
    1. Diminishing returns: Each repeated keyword match gets exponentially reduced weight
       - 1st match: full weight (1.0x)
       - 2nd match: 0.5x weight
       - 3rd match: 0.25x weight
       - Pattern: weight × 0.5^match_count (match_count starts at 0)

    2. Coverage bonus: Rewards matching diverse keywords
       - coverage_ratio = matched_groups / total_query_terms
       - coverage_multiplier = 0.8 + (coverage_ratio × 0.8)
       - Scales from 0.8x (0% coverage) to 1.6x (100% coverage)

    3. Final score = base_score × coverage_multiplier

    Args:
        query_keywords: Query keywords (normalized to lowercase)
        keyword_groups: Group indexes mapping each keyword to original position
        total_terms: Total number of original query terms (before OR expansion)
        doc_keywords: Document keywords with their scores
        doc_name: Optional document/function name for exact name matching

    Returns:
        Dictionary with:
        - score: Hybrid score with diminishing returns and coverage bonus
        - matched_keywords: List of matched keywords
        - confidence: Percentage of query keywords that matched
    """
    matched_keywords = []
    matched_groups: set[int] = set()
    base_score = 0.0

    # Track how many times each query keyword has matched (for diminishing returns)
    keyword_match_counts: defaultdict[str, int] = defaultdict(int)

    # Extract the simple name for exact name matching
    simple_name = _extract_simple_name(doc_name)

    for query_kw, group_idx in zip(query_keywords, keyword_groups, strict=False):
        # Check if keyword is in doc keywords
        if query_kw in doc_keywords:
            matched_keywords.append(query_kw)
            matched_groups.add(group_idx)

            # Apply diminishing returns: weight × 0.5^(match_count - 1)
            match_count = keyword_match_counts[query_kw]
            diminishing_factor = DIMINISHING_RETURNS_FACTOR**match_count
            base_score += doc_keywords[query_kw] * diminishing_factor

            # Increment match count for this keyword
            keyword_match_counts[query_kw] += 1

        # Also check for exact function/module name match
        # This allows searching for function names like "__init__", "__str__", etc.
        elif simple_name and query_kw == simple_name:
            matched_keywords.append(query_kw)
            matched_groups.add(group_idx)

            # Apply diminishing returns to exact name matches too
            match_count = keyword_match_counts[query_kw]
            diminishing_factor = DIMINISHING_RETURNS_FACTOR**match_count
            base_score += EXACT_NAME_MATCH_SCORE * diminishing_factor

    final_score = _apply_coverage_bonus(base_score, matched_groups, total_terms, query_keywords)

    return _build_score_result(
        final_score, matched_keywords, matched_groups, total_terms, query_keywords
    )


def calculate_wildcard_score(
    query_keywords: list[str],
    keyword_groups: list[int],
    total_terms: int,
    doc_keywords: dict[str, float],
    match_wildcard_fn: Callable[[str, str], bool],
    doc_name: str | None = None,
) -> dict[str, Any]:
    """
    Calculate search score using wildcard pattern matching with hybrid scoring.

    Applies the same hybrid scoring formula as calculate_score():
    1. Diminishing returns for repeated keyword matches
       - Pattern: weight × 0.5^match_count (match_count starts at 0)
    2. Coverage bonus for matching diverse keywords
       - coverage_ratio = matched_groups / total_query_terms

    Args:
        query_keywords: Query keywords with potential wildcards (normalized to lowercase)
        keyword_groups: Group indexes mapping each keyword to original position
        total_terms: Total number of original query terms (before OR expansion)
        doc_keywords: Document keywords with their scores
        match_wildcard_fn: Function to match wildcard patterns (pattern, text) -> bool
        doc_name: Optional document/function name for exact name matching

    Returns:
        Dictionary with:
        - score: Hybrid score with diminishing returns and coverage bonus
        - matched_keywords: List of matched query patterns
        - confidence: Percentage of query keywords that matched
    """
    matched_keywords = []
    matched_groups: set[int] = set()
    base_score = 0.0

    # Track how many times each query keyword has matched (for diminishing returns)
    keyword_match_counts: defaultdict[str, int] = defaultdict(int)

    # Extract the simple name for wildcard name matching
    simple_name = _extract_simple_name(doc_name)

    for query_kw, group_idx in zip(query_keywords, keyword_groups, strict=False):
        matched = False

        # Find all doc keywords matching this pattern
        for doc_kw, weight in doc_keywords.items():
            if match_wildcard_fn(query_kw, doc_kw):
                matched_groups.add(group_idx)
                # Add query keyword to matched list (not the doc keyword)
                if query_kw not in matched_keywords:
                    matched_keywords.append(query_kw)

                # Apply diminishing returns: weight × 0.5^match_count
                match_count = keyword_match_counts[query_kw]
                diminishing_factor = DIMINISHING_RETURNS_FACTOR**match_count
                base_score += weight * diminishing_factor

                # Increment match count
                keyword_match_counts[query_kw] += 1

                matched = True
                break

        # Also check for wildcard name match
        if not matched and simple_name and match_wildcard_fn(query_kw, simple_name):
            matched_groups.add(group_idx)
            if query_kw not in matched_keywords:
                matched_keywords.append(query_kw)

            # Apply diminishing returns to exact name matches
            match_count = keyword_match_counts[query_kw]
            diminishing_factor = DIMINISHING_RETURNS_FACTOR**match_count
            base_score += EXACT_NAME_MATCH_SCORE * diminishing_factor

            # Increment match count
            keyword_match_counts[query_kw] += 1

    final_score = _apply_coverage_bonus(base_score, matched_groups, total_terms, query_keywords)

    return _build_score_result(
        final_score, matched_keywords, matched_groups, total_terms, query_keywords
    )


def apply_module_boost(score: float, module_matched: bool) -> float:
    """
    Apply module match boost to a score.

    Args:
        score: Current score
        module_matched: Whether the module name was matched

    Returns:
        Boosted score if module was matched, otherwise unchanged
    """
    if module_matched:
        return score + MODULE_MATCH_BOOST
    return score


def filter_by_score_threshold(
    results: list[dict[str, Any]], min_score: float
) -> list[dict[str, Any]]:
    """
    Filter search results by minimum score threshold.

    Args:
        results: List of search results with 'score' field
        min_score: Minimum score threshold (0.0 to 1.0)

    Returns:
        Filtered list of results meeting the score threshold
    """
    if not results or min_score <= 0.0:
        return results

    return [r for r in results if r.get("score", 0.0) >= min_score]


def _empty_distribution_result() -> dict[str, Any]:
    """
    Return an empty distribution result with zero values.

    Returns:
        Dictionary with all distribution metrics set to zero/empty
    """
    return {
        "mean": 0.0,
        "std_dev": 0.0,
        "min_score": 0.0,
        "max_score": 0.0,
        "count": 0,
        "distribution": [],
    }


def _extract_raw_scores(scores: list[float] | list[dict[str, Any]]) -> list[float]:
    """
    Extract float scores from input, handling both raw floats and dicts with 'score' field.

    Args:
        scores: Either a list of float scores, or a list of dicts with 'score' field

    Returns:
        List of float scores
    """
    if not scores:
        return []

    if isinstance(scores[0], dict):
        return [s.get("score", 0.0) for s in scores]  # type: ignore[union-attr]
    return scores  # type: ignore[return-value]


def _calculate_statistics(raw_scores: list[float]) -> tuple[float, float, float, float]:
    """
    Calculate mean, standard deviation, min, and max for a list of scores.

    Args:
        raw_scores: List of float scores

    Returns:
        Tuple of (mean, std_dev, min_score, max_score)
    """
    n = len(raw_scores)
    mean = sum(raw_scores) / n

    if n == 1:
        std_dev = 0.0
    else:
        variance = sum((x - mean) ** 2 for x in raw_scores) / (n - 1)
        std_dev = math.sqrt(variance)

    return mean, std_dev, min(raw_scores), max(raw_scores)


def _calculate_per_score_metrics(
    raw_scores: list[float],
    mean: float,
    std_dev: float,
    min_score: float,
    max_score: float,
) -> list[dict[str, Any]]:
    """
    Calculate z-score, percentile, and normalized score for each value.

    Args:
        raw_scores: List of float scores
        mean: Average of all scores
        std_dev: Standard deviation of scores
        min_score: Minimum score in the list
        max_score: Maximum score in the list

    Returns:
        List of dicts with per-score statistics (score, z_score, percentile, normalized)
    """
    n = len(raw_scores)
    score_range = max_score - min_score

    # Create score->rank mapping for O(1) percentile lookup (optimization)
    # Sort once to avoid O(n²) complexity in percentile calculation
    sorted_scores = sorted(raw_scores)
    score_to_rank: dict[float, int] = {}

    for idx, score in enumerate(sorted_scores):
        if score not in score_to_rank:
            # Count how many scores are strictly less than this one
            score_to_rank[score] = idx

    # Calculate distribution metrics for each score
    distribution = []
    for score in raw_scores:
        # Calculate z-score (standardized score)
        z_score = (score - mean) / std_dev if std_dev > 0 else 0.0

        # Calculate percentile (what % of scores are below this) - O(1) lookup
        if score_range > 0:
            rank = score_to_rank[score]
            percentile = (rank / n) * 100
        else:
            # All scores identical - assign median percentile
            percentile = 50.0

        # Calculate normalized score (0-1 range)
        if score_range > 0:
            normalized = (score - min_score) / score_range
        else:
            normalized = NORMALIZED_SINGLE_VALUE if n == 1 else NORMALIZED_NO_VARIANCE

        distribution.append(
            {
                "score": score,
                "z_score": round(z_score, 4),
                "percentile": round(percentile, 2),
                "normalized": round(normalized, 4),
            }
        )

    return distribution


def calculate_score_distribution(
    scores: list[float] | list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate statistical distribution metrics for a list of scores.

    Computes mean, standard deviation, and for each score:
    - z-score (standardized score showing how many std devs from mean)
    - percentile (percentage of scores below this value)
    - normalized score (0-1 scale based on min-max normalization)

    Args:
        scores: Either a list of float scores, or a list of dicts with 'score' field

    Returns:
        Dictionary containing:
        - mean: Average of all scores
        - std_dev: Standard deviation of scores
        - min_score: Minimum score
        - max_score: Maximum score
        - count: Number of scores
        - distribution: List of dicts with per-score statistics:
            - score: Original score value
            - z_score: Standardized score (how many std devs from mean)
            - percentile: Percentage of scores below this value
            - normalized: Score normalized to 0-1 range

    Example:
        >>> scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        >>> dist = calculate_score_distribution(scores)
        >>> dist['mean']
        3.0
        >>> dist['std_dev']
        1.4142135623730951
    """
    # Extract raw scores from input (handles both floats and dicts)
    raw_scores = _extract_raw_scores(scores)

    if not raw_scores:
        return _empty_distribution_result()

    # Calculate statistical measures
    mean, std_dev, min_score, max_score = _calculate_statistics(raw_scores)

    # Calculate per-score metrics (z-score, percentile, normalized)
    distribution = _calculate_per_score_metrics(raw_scores, mean, std_dev, min_score, max_score)

    # Sort distribution by z-score (descending) - most relevant first
    distribution.sort(key=lambda x: x["z_score"], reverse=True)

    return {
        "mean": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "min_score": round(min_score, 4),
        "max_score": round(max_score, 4),
        "count": len(raw_scores),
        "distribution": distribution,
    }


def grade_by_z_score(z_score: float) -> dict[str, Any]:
    """
    Grade a z-score into a relevance tier with description.

    Uses standard normal distribution thresholds to categorize statistical significance:
    - Exceptional: z > 2σ (above 97.7th percentile, >2 standard deviations above mean)
    - Highly Relevant: 1σ < z ≤ 2σ (between 84th-97.7th percentile, 1-2 std devs above mean)
    - Above Average: 0 ≤ z ≤ 1σ (between 50th-84th percentile, at or above mean)
    - Below Average: -1σ < z < 0 (between 16th-50th percentile, below mean)
    - Poor: z ≤ -1σ (below 16th percentile, >1 std dev below mean)

    Args:
        z_score: The standardized score to grade

    Returns:
        Dictionary containing:
        - tier: Tier name (e.g., 'exceptional', 'highly_relevant')
        - label: Human-readable label (e.g., 'Exceptional', 'Highly Relevant')
        - description: Explanation of what this tier means
        - rank: Numeric rank (1-5, where 1 is best)

    Example:
        >>> grade_by_z_score(2.5)
        {
            'tier': 'exceptional',
            'label': 'Exceptional',
            'description': 'Top ~2% - Statistically outstanding result',
            'rank': 1
        }
    """
    if z_score > Z_SCORE_EXCEPTIONAL_THRESHOLD:
        return {
            "tier": "exceptional",
            "label": "Exceptional",
            "description": "Top ~2% - Statistically outstanding result",
            "rank": 1,
        }
    elif z_score > Z_SCORE_HIGHLY_RELEVANT_THRESHOLD:
        return {
            "tier": "highly_relevant",
            "label": "Highly Relevant",
            "description": "Top ~16% - Significantly above average",
            "rank": 2,
        }
    elif z_score >= Z_SCORE_MEAN_THRESHOLD:
        return {
            "tier": "above_average",
            "label": "Above Average",
            "description": "Top 50% - At or above average",
            "rank": 3,
        }
    elif z_score > Z_SCORE_POOR_THRESHOLD:
        return {
            "tier": "below_average",
            "label": "Below Average",
            "description": "Bottom 50% - Worse than average",
            "rank": 4,
        }
    else:
        return {
            "tier": "poor",
            "label": "Poor",
            "description": "Bottom ~16% - Significantly below average",
            "rank": 5,
        }


def calculate_score_distribution_with_tiers(
    scores: list[float] | list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate score distribution and add relevance tier grades to each result.

    This is a convenience function that combines calculate_score_distribution()
    with grade_by_z_score() to provide tier information for each score.

    Args:
        scores: Either a list of float scores, or a list of dicts with 'score' field

    Returns:
        Same structure as calculate_score_distribution(), but each distribution
        entry also includes:
        - tier: Tier name (e.g., 'exceptional')
        - tier_label: Human-readable label
        - tier_description: Explanation of the tier
        - tier_rank: Numeric rank (1-5)

    Example:
        >>> scores = [1.0, 2.0, 5.0]
        >>> result = calculate_score_distribution_with_tiers(scores)
        >>> result['distribution'][0]  # Highest z-score
        {
            'score': 5.0,
            'z_score': 1.4142,
            'percentile': 66.67,
            'normalized': 1.0,
            'tier': 'highly_relevant',
            'tier_label': 'Highly Relevant',
            'tier_description': 'Top ~16% - Significantly above average',
            'tier_rank': 2
        }
    """
    # Get base distribution
    result = calculate_score_distribution(scores)

    # Add tier grades to each distribution entry
    for dist in result["distribution"]:
        tier_info = grade_by_z_score(dist["z_score"])
        dist["tier"] = tier_info["tier"]
        dist["tier_label"] = tier_info["label"]
        dist["tier_description"] = tier_info["description"]
        dist["tier_rank"] = tier_info["rank"]

    return result


def filter_by_relevance_tier(
    distribution: list[dict[str, Any]],
    min_tier_rank: int | None = None,
    tier_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Filter distribution results by relevance tier.

    Filters can be applied by minimum tier rank (1-5 where 1 is best) or by
    specific tier names. If both filters are provided, results matching either
    condition are included (OR logic).

    Available tier names (from best to worst):
    - 'exceptional': z-score > 2.0 (above 97.7th percentile)
    - 'highly_relevant': z-score > 1.0 (between 84th-97.7th percentile)
    - 'above_average': z-score > 0.0 (between 50th-84th percentile)
    - 'below_average': z-score > -1.0 (between 16th-50th percentile)
    - 'poor': z-score ≤ -1.0 (below 16th percentile)

    Args:
        distribution: List of distribution entries with tier information
                     (from calculate_score_distribution_with_tiers)
        min_tier_rank: Include results with tier_rank ≤ this value (1=best, 5=worst)
                      Example: min_tier_rank=2 returns exceptional and highly_relevant
        tier_names: Include results with tier in this list
                   Example: ['exceptional', 'highly_relevant']

    Returns:
        Filtered list of distribution entries, maintaining z-score sort order

    Examples:
        >>> # Get only top-tier results (exceptional + highly relevant)
        >>> top_results = filter_by_relevance_tier(dist, min_tier_rank=2)

        >>> # Get exceptional results only
        >>> exceptional = filter_by_relevance_tier(dist, tier_names=['exceptional'])

        >>> # Get results above average or better
        >>> good_results = filter_by_relevance_tier(dist, min_tier_rank=3)

        >>> # Get exceptional OR highly relevant using tier names
        >>> top = filter_by_relevance_tier(dist, tier_names=['exceptional', 'highly_relevant'])
    """
    if not distribution:
        return []

    # If no filters specified, return all
    if min_tier_rank is None and tier_names is None:
        return distribution

    filtered = []

    for entry in distribution:
        # Check if entry has tier information
        if "tier_rank" not in entry or "tier" not in entry:
            continue

        include = False

        # Check tier rank filter
        if min_tier_rank is not None and entry["tier_rank"] <= min_tier_rank:
            include = True

        # Check tier names filter
        if tier_names is not None and entry["tier"] in tier_names:
            include = True

        if include:
            filtered.append(entry)

    return filtered
