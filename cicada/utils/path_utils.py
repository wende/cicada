"""
Path manipulation utilities.

This module provides centralized path normalization and resolution
functions used throughout the codebase.
"""

import os
import re
from pathlib import Path

# File type shorthand to glob pattern mapping (matches Grep tool behavior)
FILE_TYPE_TO_GLOB: dict[str, str] = {
    "py": "**/*.py",
    "ex": "**/*.{ex,exs}",
    "erl": "**/*.{erl,hrl}",
    "ts": "**/*.{ts,tsx}",
    "js": "**/*.{js,jsx}",
    "rust": "**/*.rs",
    "go": "**/*.go",
    "java": "**/*.java",
    "c": "**/*.{c,h}",
    "cpp": "**/*.{cpp,hpp,cc,hh,cxx,hxx}",
    "cs": "**/*.cs",
    "rb": "**/*.rb",
    "php": "**/*.php",
    "swift": "**/*.swift",
    "kt": "**/*.{kt,kts}",
    "scala": "**/*.{scala,sc}",
    "clj": "**/*.{clj,cljs,cljc,edn}",
    "hs": "**/*.hs",
    "ml": "**/*.{ml,mli}",
    "r": "**/*.{r,R}",
    "lua": "**/*.lua",
    "sh": "**/*.{sh,bash}",
    "sql": "**/*.sql",
    "html": "**/*.{html,htm}",
    "css": "**/*.css",
    "scss": "**/*.{scss,sass}",
    "json": "**/*.json",
    "yaml": "**/*.{yaml,yml}",
    "toml": "**/*.toml",
    "xml": "**/*.xml",
    "md": "**/*.{md,markdown}",
}


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


def is_test_file(file_path: str, language: str | None = None) -> bool:
    """
    Check if a file is a test file.

    Uses common patterns across programming languages:
    - Files in 'test/' or 'tests/' directories
    - Files with test-related suffixes (_test.*, *_test.*, test_*.*)

    Args:
        file_path: Path to the file
        language: Optional language hint (not currently used, reserved for future)

    Returns:
        True if the file is a test file

    Example:
        is_test_file('test/user_test.ex') -> True
        is_test_file('tests/test_user.py') -> True
        is_test_file('lib/user.ex') -> False
        is_test_file('src/user.py') -> False
    """
    file_lower = file_path.lower()

    # Common test directory patterns (universal)
    in_test_dir = (
        "/test/" in file_lower
        or "/tests/" in file_lower
        or file_lower.startswith(("test/", "tests/"))
    )

    # Common test file naming patterns (universal)
    # Pattern: *_test.* or test_*.* (covers most languages)
    basename = os.path.basename(file_lower)
    name_without_ext = os.path.splitext(basename)[0]
    is_test_named = name_without_ext.endswith("_test") or name_without_ext.startswith("test_")

    return in_test_dir or is_test_named


def matches_glob_pattern(file_path: str | Path, pattern: str) -> bool:
    """
    Check if file path matches a glob pattern.

    Supports:
    - * for single-level wildcards
    - ** for recursive directory matching
    - {a,b,c} for brace expansion (OR patterns)
    - ! prefix for negation (excludes matching paths)
    - Standard glob patterns

    Args:
        file_path: File path to check
        pattern: Glob pattern (e.g., "lib/**/*.ex", "!**/test/**", "**/*.{ex,heex}")

    Returns:
        True if path matches pattern (or doesn't match for negated patterns)

    Example:
        matches_glob_pattern('lib/auth/user.ex', 'lib/**/*.ex') -> True
        matches_glob_pattern('lib/user.ex', 'lib/*') -> True
        matches_glob_pattern('test/user_test.ex', '**/*_test.ex') -> True
        matches_glob_pattern('lib/user.heex', '**/*.{ex,heex}') -> True
        matches_glob_pattern('test/user_test.ex', '!**/test/**') -> False
        matches_glob_pattern('lib/user.ex', '!**/test/**') -> True
    """
    # Check for negation prefix
    negated = pattern.startswith("!")
    if negated:
        # Strip the ! prefix for matching
        pattern = pattern[1:]

    # Normalize both paths
    file_path_norm = normalize_file_path(file_path)
    pattern_norm = normalize_file_path(pattern)

    # Expand brace patterns {a,b,c} into multiple patterns
    patterns_to_test = _expand_braces(pattern_norm)

    # Test each pattern (OR logic)
    for p in patterns_to_test:
        # Convert glob pattern to regex
        # Always use regex conversion to properly handle * (should not match /)

        # Handle /** specially - it should match zero or more directory levels
        # Replace /** with a special marker first
        regex_pattern = p.replace("/**/", "/__RECURSIVEDIR__/")
        # Also handle ** at start
        if regex_pattern.startswith("**/"):
            regex_pattern = "__RECURSIVEDIR__/" + regex_pattern[3:]
        # And ** at end
        if regex_pattern.endswith("/**"):
            regex_pattern = regex_pattern[:-3] + "/__RECURSIVEDIR__"

        # Step 1: Replace remaining ** with a unique placeholder (edge case)
        regex_pattern = regex_pattern.replace("**", "__DOUBLESTAR__")
        # Step 2: Replace remaining * with a different placeholder
        regex_pattern = regex_pattern.replace("*", "__STAR__")
        # Step 3: Escape special regex characters
        regex_pattern = re.escape(regex_pattern)
        # Step 4: Replace placeholders with actual regex patterns
        # /** matches zero or more directories: (/.+)?
        # We use (/.+)? to mean "optionally, slash followed by one or more characters"
        # This makes lib/**/*.ex match both lib/user.ex and lib/auth/user.ex
        regex_pattern = regex_pattern.replace("/__RECURSIVEDIR__/", "(/.*)?/")
        # **/ at start matches zero or more directories
        regex_pattern = regex_pattern.replace("__RECURSIVEDIR__/", "(.*/)?")
        # /** at end matches zero or more directories
        regex_pattern = regex_pattern.replace("/__RECURSIVEDIR__", "(/.+)?")
        # Remaining ** (edge case, not recommended usage)
        regex_pattern = regex_pattern.replace("__DOUBLESTAR__", ".*")
        # * matches within a directory: [^/]*
        regex_pattern = regex_pattern.replace("__STAR__", "[^/]*")
        regex_pattern = "^" + regex_pattern + "$"

        if re.match(regex_pattern, file_path_norm):
            # Match found - return opposite of negation
            # If negated, we want to exclude (return False)
            # If not negated, we want to include (return True)
            return not negated

    # No match found - return same as negation
    # If negated, no match means include (return True)
    # If not negated, no match means exclude (return False)
    return negated


def _expand_braces(pattern: str) -> list[str]:
    """
    Expand brace patterns like {a,b,c} into multiple patterns.

    Args:
        pattern: Pattern possibly containing braces (e.g., "**/*.{ex,heex}")

    Returns:
        List of expanded patterns (e.g., ["**/*.ex", "**/*.heex"])

    Example:
        _expand_braces("**/*.{ex,heex}") -> ["**/*.ex", "**/*.heex"]
        _expand_braces("**/*.ex") -> ["**/*.ex"]
    """
    # Find brace expressions using regex
    brace_pattern = r"\{([^}]+)\}"
    match = re.search(brace_pattern, pattern)

    if not match:
        # No braces, return as-is
        return [pattern]

    # Extract alternatives from braces
    alternatives = match.group(1).split(",")

    # Generate patterns by replacing braces with each alternative
    expanded = []
    before = pattern[: match.start()]
    after = pattern[match.end() :]

    for alt in alternatives:
        expanded_pattern = before + alt.strip() + after
        # Recursively expand in case there are nested or multiple brace groups
        expanded.extend(_expand_braces(expanded_pattern))

    return expanded


def resolve_glob_pattern(
    glob: str | None = None,
    path: str | None = None,
    file_type: str | None = None,
) -> str | None:
    """
    Combine glob, path, and file_type into an effective glob pattern.

    This function resolves the grep-like parameters into a single glob pattern
    that can be used for file filtering. Priority: explicit glob > type mapping.
    Path acts as a prefix to the resolved pattern.

    Args:
        glob: Explicit glob pattern (e.g., "**/*.ex", "lib/**/*.py")
        path: Base directory to search in (e.g., "lib/auth", "src")
        file_type: File type shorthand (e.g., "py", "ex", "ts")

    Returns:
        Effective glob pattern, or None if no filtering specified

    Examples:
        resolve_glob_pattern(glob="*.ex") -> "*.ex"
        resolve_glob_pattern(file_type="py") -> "**/*.py"
        resolve_glob_pattern(path="lib/auth") -> "lib/auth/**/*"
        resolve_glob_pattern(path="lib", glob="*.ex") -> "lib/*.ex"
        resolve_glob_pattern(path="src", file_type="py") -> "src/**/*.py"
    """
    effective_glob = glob

    # If no explicit glob but type provided, use type mapping
    if not effective_glob and file_type:
        effective_glob = FILE_TYPE_TO_GLOB.get(file_type)

    # If path provided, prepend to glob
    if path:
        # Normalize path (remove trailing slashes)
        path_normalized = path.rstrip("/")

        if effective_glob:
            # Combine path with glob
            # Remove leading **/ from glob if present since path provides the base
            glob_normalized = effective_glob
            if glob_normalized.startswith("**/"):
                glob_normalized = glob_normalized[3:]
            effective_glob = f"{path_normalized}/{glob_normalized}"
        else:
            # Path alone: match everything under it
            effective_glob = f"{path_normalized}/**/*"

    return effective_glob
