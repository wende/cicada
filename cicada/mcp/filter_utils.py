"""
Shared filtering utilities for MCP tools.

Provides reusable filtering functions for various MCP tool operations.
"""

from typing import Any


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


def is_test_file(file_path: str) -> bool:
    """
    Determine if a file path is a test file.

    Checks for common test file patterns:
    - Contains 'test' in the path
    - Located in 'test' directory
    - Filename starts with 'test_'
    - Filename ends with '_test.ex' or '_test.exs'

    Args:
        file_path: Path to check

    Returns:
        True if the file is a test file
    """
    file_lower = file_path.lower()

    # Common test file patterns
    patterns = [
        "/test/",
        "\\test\\",  # Windows paths
        "test_",
        "_test.ex",
        "_test.exs",
    ]

    return any(pattern in file_lower for pattern in patterns)


def classify_usage_type(usage_sites: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Classify usage sites into test and production categories.

    Args:
        usage_sites: List of usage sites with 'file' field

    Returns:
        Dictionary with 'test' and 'production' keys containing categorized sites
    """
    test_sites = []
    production_sites = []

    for site in usage_sites:
        file_path = site.get("file", "")
        if is_test_file(file_path):
            test_sites.append(site)
        else:
            production_sites.append(site)

    return {
        "test": test_sites,
        "production": production_sites,
    }


def filter_by_file_type(usage_sites: list[dict[str, Any]], usage_type: str) -> list[dict[str, Any]]:
    """
    Filter usage sites by file type (test vs production).

    Args:
        usage_sites: List of usage sites with 'file' field
        usage_type: One of 'all', 'test_only', 'production_only'

    Returns:
        Filtered list of usage sites
    """
    if usage_type == "all":
        return usage_sites

    classified = classify_usage_type(usage_sites)

    if usage_type == "test_only":
        return classified["test"]
    elif usage_type == "production_only":
        return classified["production"]
    else:
        # Default to all if invalid type
        return usage_sites
