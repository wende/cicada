"""
Version checking utility.

Checks if a newer version of cicada is available on GitHub.
"""

import subprocess
import sys
from typing import Optional


def get_current_version() -> str:
    """
    Get the current version of cicada from pyproject.toml.

    Returns:
        Current version string (e.g., "0.1.0")
    """
    # For now, return hardcoded version
    # In a more robust implementation, we could parse pyproject.toml
    return "0.1.0"


def get_latest_github_tag(repo: str = "wende/cicada") -> Optional[str]:
    """
    Get the latest tag from GitHub repository.

    Args:
        repo: GitHub repository in format "owner/repo"

    Returns:
        Latest tag name, or None if unable to fetch
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/tags",
                "--jq",
                ".[0].name",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            tag = result.stdout.strip()
            # Remove 'v' prefix if present (e.g., "v0.1.0" -> "0.1.0")
            if tag.startswith("v"):
                tag = tag[1:]
            return tag

        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Silently fail - this is a non-critical check
        return None


def compare_versions(current: str, latest: str) -> bool:
    """
    Compare two version strings.

    Args:
        current: Current version (e.g., "0.1.0")
        latest: Latest version (e.g., "0.2.0")

    Returns:
        True if latest is newer than current, False otherwise
    """
    try:
        # Simple comparison by splitting on dots
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]

        # Pad with zeros if needed
        max_len = max(len(current_parts), len(latest_parts))
        current_parts += [0] * (max_len - len(current_parts))
        latest_parts += [0] * (max_len - len(latest_parts))

        return latest_parts > current_parts

    except (ValueError, AttributeError):
        # If we can't parse versions, assume they're the same
        return False


def check_for_updates() -> None:
    """
    Check if there's a newer version available on GitHub.

    Prints a yellow warning message if a newer version is found.
    This function never raises exceptions - it fails silently if unable to check.
    """
    try:
        current = get_current_version()
        latest = get_latest_github_tag()

        if latest and compare_versions(current, latest):
            # ANSI escape code for yellow text
            yellow = "\033[93m"
            reset = "\033[0m"

            print(f"{yellow}⚠️  A newer version of cicada is available: v{latest} (current: v{current}){reset}")
            print(f"{yellow}   To update, run:{reset}")
            print(f"{yellow}   uv tool install git+https://github.com/wende/cicada.git{reset}")
            print()

    except Exception:
        # Silently fail - version check is non-critical
        pass
