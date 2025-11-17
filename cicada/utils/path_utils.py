"""
Path manipulation utilities.

This module provides centralized path normalization and resolution
functions used throughout the codebase.
"""

import fnmatch
import re
from pathlib import Path


def normalize_file_path(
    file_path: str | Path,
    strip_leading_dot: bool = True,
    strip_trailing_whitespace: bool = True,
) -> str:
    """
    Normalize a file path for consistent comparisons.

    Args:
        file_path: Path to normalize
        strip_leading_dot: Remove leading './' if present
        strip_trailing_whitespace: Remove trailing whitespace

    Returns:
        Normalized path string

    Example:
        normalize_file_path('./lib/user.ex') -> 'lib/user.ex'
        normalize_file_path('  lib/user.ex  ') -> 'lib/user.ex'
    """
    path_str = str(file_path)

    if strip_trailing_whitespace:
        path_str = path_str.strip()

    if strip_leading_dot:
        # Remove leading './' prefix (not individual '.' or '/' characters)
        while path_str.startswith("./"):
            path_str = path_str[2:]

    return path_str


def resolve_to_repo_root(
    file_path: str | Path,
    repo_root: str | Path,
) -> Path:
    """
    Resolve a file path relative to repository root.

    Handles both absolute and relative paths, converting absolute paths
    to be relative to the repository root.

    Args:
        file_path: Path to resolve (can be absolute or relative)
        repo_root: Repository root directory

    Returns:
        Path relative to repo root

    Raises:
        ValueError: If absolute path is not within repo root

    Example:
        resolve_to_repo_root('/repo/lib/user.ex', '/repo') -> Path('lib/user.ex')
        resolve_to_repo_root('lib/user.ex', '/repo') -> Path('lib/user.ex')
    """
    file_path_obj = Path(file_path)
    repo_root_obj = Path(repo_root).resolve()

    # If already relative, return as-is
    if not file_path_obj.is_absolute():
        return file_path_obj

    # Convert absolute to relative
    try:
        return file_path_obj.relative_to(repo_root_obj)
    except ValueError:
        raise ValueError(f"File path {file_path} is not within repository {repo_root}") from None


def match_file_path(
    candidate: str | Path,
    target: str | Path,
    normalize: bool = True,
) -> bool:
    """
    Check if two file paths match, with flexible matching rules.

    Supports:
    - Exact match
    - Candidate ends with target
    - Target ends with candidate

    Args:
        candidate: File path to check
        target: Target file path
        normalize: Whether to normalize paths before comparison

    Returns:
        True if paths match

    Example:
        match_file_path('lib/user.ex', 'lib/user.ex') -> True
        match_file_path('/repo/lib/user.ex', 'lib/user.ex') -> True
        match_file_path('user.ex', 'lib/user.ex') -> True
    """
    if normalize:
        candidate_str = normalize_file_path(candidate)
        target_str = normalize_file_path(target)
    else:
        candidate_str = str(candidate)
        target_str = str(target)

    # Exact match
    if candidate_str == target_str:
        return True

    # Candidate ends with target (absolute path provided, target is relative)
    if candidate_str.endswith(target_str):
        return True

    # Target ends with candidate (partial path provided)
    return bool(target_str.endswith(candidate_str))


def is_git_repository(path: str | Path) -> bool:
    """
    Check if a path is a git repository.

    Args:
        path: Path to check

    Returns:
        True if the path is a git repository, False otherwise

    Example:
        is_git_repository('/repo') -> True
        is_git_repository('/not/a/repo') -> False
    """
    git_dir = Path(path) / ".git"
    return git_dir.exists()


def find_repo_root(start_path: str | Path | None = None) -> Path | None:
    """
    Find the git repository root starting from a given path.

    Args:
        start_path: Path to start searching from (default: current directory)

    Returns:
        Path to repository root, or None if not in a git repo

    Example:
        find_repo_root('/repo/lib/user') -> Path('/repo')
        find_repo_root('/not/a/repo') -> None
    """
    current = Path.cwd() if start_path is None else Path(start_path).resolve()

    # Walk up the directory tree looking for .git
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent

    return None


def ensure_relative_to_repo(
    file_path: str | Path,
    repo_root: str | Path,
) -> str:
    """
    Ensure a file path is relative to the repository root.

    This is a convenience function that combines normalization and
    resolution. If the path is already relative, it's normalized.
    If it's absolute, it's converted to relative.

    Args:
        file_path: File path to process
        repo_root: Repository root directory

    Returns:
        Normalized path string relative to repo root

    Example:
        ensure_relative_to_repo('/repo/./lib/user.ex', '/repo') -> 'lib/user.ex'
        ensure_relative_to_repo('lib/user.ex', '/repo') -> 'lib/user.ex'
    """
    resolved = resolve_to_repo_root(file_path, repo_root)
    return normalize_file_path(resolved)


def is_test_file(file_path: str) -> bool:
    """
    Check if a file is a test file or script file.

    Files are considered test/script files if they:
    - Are in 'test/' directory (anywhere in path or at start)
    - End with '_test.ex' suffix
    - End with '.exs' extension (Elixir script files)

    Args:
        file_path: Path to the file

    Returns:
        True if the file is a test file or script

    Example:
        is_test_file('test/user_test.ex') -> True
        is_test_file('lib/mix_task.exs') -> True
        is_test_file('lib/user.ex') -> False
    """
    file_lower = file_path.lower()
    return (
        "/test/" in file_lower
        or file_lower.startswith("test/")
        or file_lower.endswith(("_test.ex", ".exs"))
    )


def matches_glob_pattern(file_path: str | Path, pattern: str) -> bool:
    """
    Check if file path matches a glob pattern.

    Supports:
    - * for single-level wildcards
    - ** for recursive directory matching
    - Standard glob patterns

    Args:
        file_path: File path to check
        pattern: Glob pattern (e.g., "lib/**/*.ex", "**/*_test.ex")

    Returns:
        True if path matches pattern

    Example:
        matches_glob_pattern('lib/auth/user.ex', 'lib/**/*.ex') -> True
        matches_glob_pattern('lib/user.ex', 'lib/*') -> True
        matches_glob_pattern('test/user_test.ex', '**/*_test.ex') -> True
    """
    # Normalize both paths
    file_path_norm = normalize_file_path(file_path)
    pattern_norm = normalize_file_path(pattern)

    # Handle ** recursive matching
    if "**" in pattern_norm:
        # Convert glob pattern to regex
        regex_pattern = pattern_norm.replace("**", ".*").replace("*", "[^/]*")
        regex_pattern = "^" + regex_pattern + "$"
        return bool(re.match(regex_pattern, file_path_norm))

    # Use fnmatch for simple patterns
    return fnmatch.fnmatch(file_path_norm, pattern_norm)
