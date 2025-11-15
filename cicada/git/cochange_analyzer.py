"""Co-change analysis from git history.

This module analyzes git commit history to identify files and functions
that are frequently changed together, revealing conceptual relationships
that code dependencies don't show.
"""

import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class CoChangeAnalyzer:
    """Analyzes git history to find co-change patterns."""

    def analyze_repository(
        self, repo_path: str, since_date: datetime | None = None, min_count: int = 1
    ) -> dict:
        """Analyze git repository for co-change patterns.

        Args:
            repo_path: Path to git repository
            since_date: Only analyze commits after this date (optional)
            min_count: Minimum co-change count to include in results

        Returns:
            Dictionary containing:
            - file_pairs: Dict of (file1, file2) -> co-change count
            - function_pairs: Dict of (func1, func2) -> co-change count
            - metadata: Analysis metadata (timestamp, commit count, etc.)
        """
        repo_path_obj = Path(repo_path).resolve()

        # Get commit log
        commits = self._get_commits(repo_path_obj, since_date)

        # Analyze file-level co-changes
        file_pairs = self._analyze_file_cochanges(repo_path_obj, commits, min_count)

        # Analyze function-level co-changes
        function_pairs = self._analyze_function_cochanges(repo_path_obj, commits, min_count)

        # Count unique pairs
        unique_file_pairs = len({tuple(sorted(pair)) for pair in file_pairs})
        unique_function_pairs = len({tuple(sorted(pair)) for pair in function_pairs})

        return {
            "file_pairs": file_pairs,
            "function_pairs": function_pairs,
            "metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "commit_count": len(commits),
                "file_pairs": unique_file_pairs,
                "function_pairs": unique_function_pairs,
            },
        }

    def _get_commits(self, repo_path: Path, since_date: datetime | None = None) -> list:
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
        except subprocess.CalledProcessError:
            return []

    def _analyze_file_cochanges(
        self, repo_path: Path, commits: list, min_count: int
    ) -> dict[tuple[str, str], int]:
        """Analyze file-level co-changes.

        Args:
            repo_path: Path to repository
            commits: List of commit SHAs
            min_count: Minimum count threshold

        Returns:
            Dictionary mapping (file1, file2) -> count
        """
        cochange_counts = defaultdict(int)

        for commit_sha in commits:
            files = self._get_files_in_commit(repo_path, commit_sha)

            # Skip single-file commits (no co-change possible)
            if len(files) < 2:
                continue

            # Record all pairs
            for i, file1 in enumerate(files):
                for file2 in files[i + 1 :]:
                    # Store both orderings
                    cochange_counts[(file1, file2)] += 1
                    cochange_counts[(file2, file1)] += 1

        # Filter by minimum count
        return {pair: count for pair, count in cochange_counts.items() if count >= min_count}

    def _analyze_function_cochanges(
        self, repo_path: Path, commits: list, min_count: int
    ) -> dict[tuple[str, str], int]:
        """Analyze function-level co-changes.

        Args:
            repo_path: Path to repository
            commits: List of commit SHAs
            min_count: Minimum count threshold

        Returns:
            Dictionary mapping (func1, func2) -> count
        """
        cochange_counts = defaultdict(int)

        for commit_sha in commits:
            functions = self._get_functions_in_commit(repo_path, commit_sha)

            # Skip commits with 0 or 1 function changed
            if len(functions) < 2:
                continue

            # Record all pairs
            for i, func1 in enumerate(functions):
                for func2 in functions[i + 1 :]:
                    # Store both orderings
                    cochange_counts[(func1, func2)] += 1
                    cochange_counts[(func2, func1)] += 1

        # Filter by minimum count
        return {pair: count for pair, count in cochange_counts.items() if count >= min_count}

    def _get_files_in_commit(self, repo_path: Path, commit_sha: str) -> list:
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
        except subprocess.CalledProcessError:
            return []

    def _get_functions_in_commit(self, repo_path: Path, commit_sha: str) -> list:
        """Get list of functions modified in a commit.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA

        Returns:
            List of function signatures (e.g., "ModuleName.func_name/arity")
        """
        functions = set()

        # Get files modified in this commit
        files = self._get_files_in_commit(repo_path, commit_sha)

        # For each Elixir file, extract all function definitions
        # Heuristic: If a file is modified, we consider all its functions as potentially modified
        # This is simpler than trying to track exact function changes via diff analysis
        for file_path in files:
            if not file_path.endswith((".ex", ".exs")):
                continue

            module_name = self._extract_module_name(repo_path, commit_sha, file_path)
            if not module_name:
                continue

            # Get file content at this commit
            try:
                result = subprocess.run(
                    ["git", "show", f"{commit_sha}:{file_path}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                content = result.stdout

                # Extract all function definitions
                for line in content.split("\n"):
                    func_match = re.search(r"^\s*def[p]?\s+([a-z_][a-z0-9_]*)\s*\(([^)]*)\)", line)
                    if func_match:
                        func_name = func_match.group(1)
                        params = func_match.group(2)

                        # Count arity (number of parameters)
                        if params.strip():
                            # Simple arity counting - split by comma
                            arity = len([p for p in params.split(",") if p.strip()])
                        else:
                            arity = 0

                        function_sig = f"{module_name}.{func_name}/{arity}"
                        functions.add(function_sig)

            except subprocess.CalledProcessError:
                continue

        return list(functions)

    def _extract_module_name(self, repo_path: Path, commit_sha: str, file_path: str) -> str | None:
        """Extract the module name from a file.

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA
            file_path: Path to file (relative to repo)

        Returns:
            Module name or None
        """
        # Skip non-Elixir files
        if not file_path.endswith(".ex") and not file_path.endswith(".exs"):
            return None

        try:
            # Get file content at this commit
            result = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            content = result.stdout

            # Look for defmodule declaration
            module_match = re.search(r"defmodule\s+([A-Z][A-Za-z0-9_.]*)\s+do", content)
            if module_match:
                return module_match.group(1)

        except subprocess.CalledProcessError:
            pass

        return None
