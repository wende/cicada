"""Co-change analysis from git history.

This module analyzes git commit history to identify files and functions
that are frequently changed together, revealing conceptual relationships
that code dependencies don't show.
"""

import logging
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Regex patterns for parsing Elixir code
# Note: Elixir allows ? and ! in function names (e.g., empty?, save!)
ELIXIR_FUNCTION_PATTERN = re.compile(
    r"^\s*def[p]?\s+([a-z_][a-z0-9_?!]*)\s*\(([^)]*)\)", re.MULTILINE
)
ELIXIR_MODULE_PATTERN = re.compile(r"defmodule\s+([A-Z][A-Za-z0-9_.]*)\s+do")


class CoChangeAnalyzer:
    """Analyzes git history to find co-change patterns."""

    @staticmethod
    def find_cochange_pairs(
        target: str, pairs: dict[tuple[str, str], int]
    ) -> list[tuple[str, int]]:
        """
        Find all items that co-changed with the target.

        Pairs are stored in canonical (sorted) order, so we need to check both positions.

        Args:
            target: The item to find co-changes for
            pairs: Dictionary of canonical (sorted) pairs to counts

        Returns:
            List of (related_item, count) tuples
        """
        results = []
        for (item1, item2), count in pairs.items():
            if item1 == target:
                results.append((item2, count))
            elif item2 == target:
                results.append((item1, count))
        return results

    def analyze_repository(
        self, repo_path: str, since_date: datetime | None = None, min_count: int = 1
    ) -> dict[str, Any]:
        """Analyze git repository for co-change patterns.

        Args:
            repo_path: Path to git repository
            since_date: Only analyze commits after this date (optional)
            min_count: Minimum co-change count to include in results

        Returns:
            Dictionary containing:
            - file_pairs: Dict of canonical (file1, file2) tuples -> co-change count
            - function_pairs: Dict of canonical (func1, func2) tuples -> co-change count
            - metadata: Analysis metadata (timestamp, commit count, etc.)
        """
        repo_path_obj = Path(repo_path).resolve()

        # Get commit log
        commits = self._get_commits(repo_path_obj, since_date)

        # Analyze file-level co-changes
        file_pairs = self._analyze_cochanges(
            repo_path_obj, commits, min_count, self._get_files_in_commit
        )

        # Analyze function-level co-changes
        function_pairs = self._analyze_cochanges(
            repo_path_obj, commits, min_count, self._get_functions_in_commit
        )

        return {
            "file_pairs": file_pairs,
            "function_pairs": function_pairs,
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "commit_count": len(commits),
                "file_pairs": len(file_pairs),
                "function_pairs": len(function_pairs),
            },
        }

    def _get_commits(self, repo_path: Path, since_date: datetime | None = None) -> list[str]:
        """Get list of commit SHAs from repository.

        Args:
            repo_path: Path to repository
            since_date: Only include commits after this date

        Returns:
            List of commit SHA strings
        """
        cmd = ["git", "log", "--format=%H"]

        if since_date:
            since_str = since_date.strftime("%Y-%m-%d")
            cmd.append(f"--since={since_str}")

        try:
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
            commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            return commits
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to get commits from {repo_path}: {e.stderr.strip() if e.stderr else 'unknown error'}"
            )
            return []
        except FileNotFoundError:
            logger.error(f"Git not found in PATH. Cannot analyze repository {repo_path}")
            return []

    def _analyze_cochanges(
        self,
        repo_path: Path,
        commits: list[str],
        min_count: int,
        item_extractor: Callable[[Path, str], list[str]],
    ) -> dict[tuple[str, str], int]:
        """Generic co-change analysis for any item type (files, functions, etc).

        This method uses canonical (sorted) pair representation to avoid
        storing redundant bidirectional relationships.

        Args:
            repo_path: Path to repository
            commits: List of commit SHAs
            min_count: Minimum count threshold
            item_extractor: Function that extracts items from a commit

        Returns:
            Dictionary mapping canonical (sorted) item pairs to co-change counts
        """
        cochange_counts = defaultdict(int)

        for commit_sha in commits:
            items = item_extractor(repo_path, commit_sha)

            # Skip commits with less than 2 items (no co-change possible)
            if len(items) < 2:
                continue

            # Generate all unique pairs using canonical ordering
            # combinations ensures we only generate (A, B) not (B, A)
            # sorted ensures consistent ordering (e.g., always alphabetical)
            for item1, item2 in combinations(sorted(items), 2):
                pair = (item1, item2)
                cochange_counts[pair] += 1

        # Filter by minimum count
        return {pair: count for pair, count in cochange_counts.items() if count >= min_count}

    def _get_files_in_commit(self, repo_path: Path, commit_sha: str) -> list[str]:
        """Get list of files modified in a commit.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA

        Returns:
            List of file paths (relative to repo root)
        """
        try:
            # Use --name-only to get just file names
            # Note: --follow only works with single file, so we use --diff-filter
            # to track renames via R flag
            result = subprocess.run(
                ["git", "show", "--name-only", "--format=", commit_sha],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            return files
        except subprocess.CalledProcessError as e:
            logger.debug(
                f"Failed to get files for commit {commit_sha[:7]}: {e.stderr.strip() if e.stderr else 'unknown error'}"
            )
            return []

    def _get_functions_in_commit(self, repo_path: Path, commit_sha: str) -> list[str]:
        """Get list of functions modified in a commit.

        Heuristic: If a file is modified, we consider all its functions as potentially modified.
        This is simpler than trying to track exact function changes via diff analysis.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA

        Returns:
            List of function signatures (e.g., "ModuleName.func_name/arity")
        """
        functions = set()
        files = self._get_files_in_commit(repo_path, commit_sha)

        for file_path in self._filter_elixir_files(files):
            module_name = self._extract_module_name(repo_path, commit_sha, file_path)
            if not module_name:
                continue

            content = self._get_file_content_at_commit(repo_path, commit_sha, file_path)
            if content is None:
                continue

            file_functions = self._extract_function_signatures(content, module_name)
            functions.update(file_functions)

        return list(functions)

    def _filter_elixir_files(self, files: list[str]) -> list[str]:
        """Filter list to include only Elixir files.

        Args:
            files: List of file paths

        Returns:
            List of Elixir file paths (.ex and .exs files)
        """
        return [f for f in files if f.endswith((".ex", ".exs"))]

    def _get_file_content_at_commit(
        self, repo_path: Path, commit_sha: str, file_path: str
    ) -> str | None:
        """Get file content at a specific commit.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA
            file_path: Path to file (relative to repo)

        Returns:
            File content as string, or None if retrieval failed
        """
        try:
            result = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.debug(
                f"Failed to get content for {file_path} at {commit_sha[:7]}: "
                f"{e.stderr.strip() if e.stderr else 'unknown error'}"
            )
            return None

    def _extract_function_signatures(self, content: str, module_name: str) -> set[str]:
        """Extract all function signatures from Elixir code content.

        Args:
            content: Elixir source code
            module_name: Module name for the functions

        Returns:
            Set of function signatures (e.g., {"ModuleName.func_name/2"})
        """
        # Module name should start with uppercase (Elixir convention)
        if not module_name or not module_name[0].isupper():
            return set()

        signatures = set()
        for match in ELIXIR_FUNCTION_PATTERN.finditer(content):
            func_name = match.group(1)
            # Function name should start with lowercase (Elixir convention)
            # The regex pattern already enforces this, so this check is defensive
            if func_name and func_name[0].islower():
                arity = self._calculate_arity(match.group(2))
                signatures.add(f"{module_name}.{func_name}/{arity}")

        return signatures

    def _calculate_arity(self, params: str) -> int:
        """Calculate function arity from parameter string.

        This uses a simple comma-counting heuristic that works for most cases
        but may be inaccurate for complex patterns like:
        - Functions with default arguments: foo(x, y \\\\ [])
        - Pattern matched parameters: foo(%{a: x}, [h | t])
        - Functions with map literals: foo(%{key: 1, key2: 2})

        This is acceptable because co-change analysis cares about relationships,
        not exact arity values. Functions will still be tracked correctly even
        if arity is off by one.

        Args:
            params: Function parameter string from regex match

        Returns:
            Approximate arity (parameter count)
        """
        if not params.strip():
            return 0
        return len([p for p in params.split(",") if p.strip()])

    def _extract_module_name(self, repo_path: Path, commit_sha: str, file_path: str) -> str | None:
        """Extract the module name from an Elixir file.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA
            file_path: Path to Elixir file (must be .ex or .exs, caller ensures this)

        Returns:
            Module name or None if not found
        """
        content = self._get_file_content_at_commit(repo_path, commit_sha, file_path)
        if content is None:
            return None

        # Look for defmodule declaration using pre-compiled pattern
        module_match = ELIXIR_MODULE_PATTERN.search(content)
        if module_match:
            return module_match.group(1)

        return None
