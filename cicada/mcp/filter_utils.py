"""
Shared filtering utilities for MCP tools.

Provides reusable filtering functions for various MCP tool operations.
"""

from typing import Any

from cicada.scoring import filter_by_score_threshold

# Re-export for backward compatibility
__all__ = [
    "filter_by_score_threshold",
    "is_test_file",
    "classify_usage_type",
    "filter_by_file_type",
]


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
    Filter usage sites by file type (test vs source).

    Args:
        usage_sites: List of usage sites with 'file' field
        usage_type: One of 'all', 'tests', 'source'

    Returns:
        Filtered list of usage sites
    """
    if usage_type == "all":
        return usage_sites

    classified = classify_usage_type(usage_sites)

    if usage_type == "tests" or usage_type == "test_only":  # Keep backward compatibility
        return classified["test"]
    elif usage_type == "source" or usage_type == "production_only":  # Keep backward compatibility
        return classified["production"]
    else:
        # Default to source for invalid type
        return classified["production"]
