"""
Version checking utility.

Checks if a newer version of cicada is available on GitHub.
"""

import subprocess


def get_git_tag() -> str | None:
    """
    Get the most recent git tag from build-time generated file.

    Returns:
        Git tag (e.g., "v0.2.0-rc1"), or None if not available
    """
    try:
        from cicada._version_hash import GIT_TAG

        if GIT_TAG and GIT_TAG != "unknown":
            return GIT_TAG
    except (ImportError, AttributeError):
        pass

    return None


def get_git_commit_hash() -> str | None:
    """
    Get the current git commit hash from build-time generated file.

    Returns:
        Git commit hash (7-char short form), or None if not available
    """
    try:
        from cicada._version_hash import GIT_HASH

        if GIT_HASH and GIT_HASH != "unknown":
            return GIT_HASH
    except ImportError:
        pass

    return None


def get_current_version() -> str:
    """
    Get the current version of cicada from pyproject.toml.

    Returns:
        Current version string (e.g., "0.1.0")
    """
    from cicada import __version__

    return __version__


def get_latest_github_tag(repo: str = "wende/cicada") -> str | None:
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


def get_version_string() -> str:
    """
    Get a formatted version string including git tag and commit hash if available.

    Returns:
        Version string in format:
        - "0.2.0" (no git info)
        - "0.2.0 (v0.2.0-rc1/abc1234)" (with tag and hash)
        - "0.2.0 (abc1234)" (hash only, no tag)
    """
    version = get_current_version()
    git_tag = get_git_tag()
    commit_hash = get_git_commit_hash()

    # Build git info string
    git_info_parts = []
    if git_tag:
        git_info_parts.append(git_tag)
    if commit_hash:
        git_info_parts.append(commit_hash)

    if git_info_parts:
        git_info = "/".join(git_info_parts)
        return f"{version} ({git_info})"
    return version


def extract_version_tag(version_string: str) -> str:
    """
    Extract the pyproject version tag from a version string.

    Args:
        version_string: Version string like "0.2.2" or "0.2.2 (v0.2.2/0991325)"

    Returns:
        Just the version tag (e.g., "0.2.2")
    """
    # Split on space and take the first part (before any git info in parentheses)
    return version_string.split()[0] if version_string else ""


def version_mismatch(stored_version: str | None, current_version: str | None) -> bool:
    """
    Check if the stored version differs from the current version.

    Only compares version tags (pyproject version), ignoring git tags and commit hashes.

    Args:
        stored_version: Version string from index.json metadata
        current_version: Current cicada version string

    Returns:
        True if versions differ (or if stored_version is missing), False if they match
    """
    if not stored_version:
        return True

    stored_tag = extract_version_tag(stored_version)
    current_tag = extract_version_tag(current_version or get_version_string())

    return stored_tag != current_tag


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

            print(
                f"{yellow}⚠️  A newer version of cicada is available: v{latest} (current: v{current}){reset}"
            )
            print(f"{yellow}   To update, run:{reset}")
            print(f"{yellow}   uv tool install git+https://github.com/wende/cicada.git{reset}")
            print()

    except Exception:
        # Silently fail - version check is non-critical
        pass
