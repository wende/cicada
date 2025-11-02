"""
Path manipulation utilities.

This module provides centralized path normalization and resolution
functions used throughout the codebase.
"""

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


def ensure_gitignore_has_cicada(repo_root: str | Path) -> bool:
    """
    Ensure .gitignore contains .cicada/ directory entry.

    If .gitignore exists and doesn't already contain .cicada/, adds it.
    If .gitignore doesn't exist, this function does nothing.

    Args:
        repo_root: Repository root directory

    Returns:
        True if .cicada/ was added to .gitignore, False otherwise

    Example:
        ensure_gitignore_has_cicada('/repo') -> True (if added)
        ensure_gitignore_has_cicada('/repo') -> False (if already present or no .gitignore)
    """
    repo_root_path = Path(repo_root).resolve()
    gitignore_path = repo_root_path / ".gitignore"

    # Do nothing if .gitignore doesn't exist
    if not gitignore_path.exists():
        return False

    try:
        # Read existing .gitignore
        with open(gitignore_path) as f:
            content = f.read()

        # Check if .cicada/ is already present in actual gitignore patterns
        # (ignore comment lines starting with #)
        for line in content.splitlines():
            # Strip whitespace and skip empty lines and comments
            stripped = line.strip()
            # Check if this line contains .cicada as a gitignore pattern
            # Valid patterns: .cicada, .cicada/, /.cicada, /.cicada/, **/.cicada/, etc.
            if (
                stripped
                and not stripped.startswith("#")
                and (
                    stripped in (".cicada", ".cicada/")
                    or stripped.endswith(("/.cicada", "/.cicada/"))
                )
            ):
                return False

        # Add .cicada/ to .gitignore
        with open(gitignore_path, "a") as f:
            # Add newline if file doesn't end with one
            if content and not content.endswith("\n"):
                f.write("\n")

            f.write(".cicada/\n")

        return True

    except OSError:
        # Fail silently if we can't read/write the file
        return False
