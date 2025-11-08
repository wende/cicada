"""
Fuzzy matching utilities for finding similar names.

This module provides utilities for finding similar module and function names
using fuzzy string matching algorithms.
"""

from difflib import SequenceMatcher


def find_similar_names(
    query: str, candidates: list[str], max_suggestions: int = 5, threshold: float = 0.4
) -> list[tuple[str, float]]:
    """
    Find similar names using fuzzy matching.

    Args:
        query: The query string to match
        candidates: List of candidate names to match against
        max_suggestions: Maximum number of suggestions to return
        threshold: Minimum similarity score (0.0-1.0) to include in results

    Returns:
        List of (name, similarity_score) tuples, sorted by similarity (descending)
    """
    similarities: list[tuple[str, float]] = []
    query_lower = query.lower()

    # Early exit for exact match
    for candidate in candidates:
        if query_lower == candidate.lower():
            return [(candidate, 1.0)]

    # Limit search space for very large indices to prevent performance issues
    search_candidates = candidates[:500] if len(candidates) > 500 else candidates

    for candidate in search_candidates:
        # Calculate base similarity score
        similarity = SequenceMatcher(None, query_lower, candidate.lower()).ratio()

        # Boost score for substring matches
        if query_lower in candidate.lower():
            similarity = max(similarity, 0.7)

        # Boost score for partial component matches (e.g., "User" matches "MyApp.User")
        query_parts = query.split(".")
        if any(qpart.lower() in candidate.lower() for qpart in query_parts):
            similarity = max(similarity, 0.6)

        similarities.append((candidate, similarity))

    # Sort by similarity (descending) and return top matches above threshold
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [(name, score) for name, score in similarities[:max_suggestions] if score > threshold]
