"""
Git integration - extract commit history and file changes

This module provides access to git commit history using GitPython.
It complements pr_finder.py (which provides PR attribution) by
offering comprehensive commit history for files and functions.

Author: Cursor(Auto)
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import git


class GitHelper:
    """Helper class for extracting git commit history"""

    @staticmethod
    def _extract_pr_number(message: str) -> int | None:
        """
        Extract PR number from commit message.

        Looks for patterns like (#123) or (PR #123) at the end of the message.

        Args:
            message: Commit message

        Returns:
            PR number as integer, or None if not found
        """
        import re

        # Match (#123) or (PR #123) or similar patterns
        match = re.search(r"\((?:PR )?#(\d+)\)", message)
        if match:
            return int(match.group(1))
        return None

    def __init__(self, repo_path: str):
        """
        Initialize GitHelper with a repository path

        Args:
            repo_path: Path to git repository

        Raises:
            git.InvalidGitRepositoryError: If path is not a git repository
        """
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)

    def get_file_history(self, file_path: str, max_commits: int = 10) -> list[dict]:
        """
        Get commit history for a specific file

        Args:
            file_path: Relative path to file from repo root
            max_commits: Maximum number of commits to return

        Returns:
            List of commit information dictionaries with keys:
            - sha: Short commit SHA (8 chars)
            - full_sha: Full commit SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date in ISO format
            - message: Full commit message
            - summary: First line of commit message
        """
        commits = []

        try:
            # Get commits that touched this file
            for commit in self.repo.iter_commits(paths=file_path, max_count=max_commits):
                commits.append(
                    {
                        "sha": commit.hexsha[:8],  # Short SHA
                        "full_sha": commit.hexsha,
                        "author": str(commit.author),
                        "author_email": commit.author.email,
                        "date": commit.committed_datetime.isoformat(),
                        "message": commit.message.strip(),
                        "summary": commit.summary,
                    }
                )
        except Exception as e:
            print(f"Error getting history for {file_path}: {e}")

        return commits

    def get_function_history_heuristic(
        self,
        file_path: str,
        function_name: str,
        max_commits: int = 5,
    ) -> list[dict]:
        """
        Get commit history for a specific function using heuristics.

        This is a heuristic-based approach that returns commits that:
        1. Modified the file near the function's location, OR
        2. Mention the function name in the commit message

        A more sophisticated version would use git blame to track
        exact line changes over time.

        Args:
            file_path: Relative path to file
            function_name: Name of the function
            line_number: Line number where function is defined
            max_commits: Maximum commits to return

        Returns:
            List of relevant commits with 'relevance' field:
            - 'mentioned': Function name in commit message
            - 'file_change': Recent change to the file
        """
        # Get file history with more commits than requested
        file_commits = self.get_file_history(file_path, max_commits * 2)

        # Filter for commits mentioning the function or likely relevant
        relevant_commits = []
        for commit in file_commits:
            # Include if function name in commit message
            if function_name.lower() in commit["message"].lower():
                commit["relevance"] = "mentioned"
                relevant_commits.append(commit)
            # Or if it's a recent commit to the file
            elif len(relevant_commits) < max_commits:
                commit["relevance"] = "file_change"
                relevant_commits.append(commit)

            if len(relevant_commits) >= max_commits:
                break

        return relevant_commits

    def get_function_history_precise(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        function_name: str | None = None,
        max_commits: int = 5,
    ) -> list[dict]:
        """
        Get precise commit history for a function using git log -L.

        This method uses git's native function tracking (when function_name is provided)
        or line tracking (when start_line/end_line are provided) to find commits that
        actually modified the function, even as it moves within the file.

        Args:
            file_path: Relative path to file from repo root
            start_line: Starting line number (optional, for line-based tracking)
            end_line: Ending line number (optional, for line-based tracking)
            function_name: Function name to track (e.g., "create_user")
            max_commits: Maximum number of commits to return

        Returns:
            List of commit information dictionaries with keys:
            - sha: Short commit SHA (8 chars)
            - full_sha: Full commit SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date in ISO format
            - message: Full commit message
            - summary: First line of commit message

        Note:
            - Provide either function_name OR (start_line, end_line)
            - If function_name is provided and fails, falls back to line-based tracking
            - Requires .gitattributes with "*.ex diff=elixir" for function tracking
        """
        commits = []

        # Determine tracking mode
        use_function_tracking = function_name is not None
        use_line_tracking = start_line is not None and end_line is not None

        if not use_function_tracking and not use_line_tracking:
            print("Error: Must provide either function_name or (start_line, end_line)")
            return []

        try:
            # Build git log -L command
            if use_function_tracking:
                # Try function-based tracking first: git log -L :funcname:file
                line_spec = f":{function_name}:{file_path}"
            else:
                # Use line-based tracking: git log -L start,end:file
                line_spec = f"{start_line},{end_line}:{file_path}"

            cmd = [
                "git",
                "log",
                f"-L{line_spec}",
                f"--max-count={max_commits}",
                "--format=%H|%an|%ae|%aI|%s",
                "--no-patch",  # Don't show diffs, just commits
            ]

            # Run command in repo directory
            result = subprocess.run(
                cmd, cwd=str(self.repo_path), capture_output=True, text=True, check=True
            )

            # Parse output
            for line in result.stdout.strip().split("\n"):
                if not line or line.startswith("diff"):
                    continue

                parts = line.split("|")
                if len(parts) >= 5:
                    full_sha = parts[0]
                    commits.append(
                        {
                            "sha": full_sha[:8],
                            "full_sha": full_sha,
                            "author": parts[1],
                            "author_email": parts[2],
                            "date": parts[3],
                            "summary": parts[4],
                            "message": parts[4],  # Summary for now, can enhance later
                        }
                    )

        except subprocess.CalledProcessError:
            # git log -L failed
            # If function tracking failed and we have line numbers, try fallback
            if use_function_tracking and start_line and end_line:
                # Silently try line-based tracking as fallback
                return self.get_function_history_precise(
                    file_path,
                    start_line=start_line,
                    end_line=end_line,
                    max_commits=max_commits,
                )
            else:
                # Silently skip - git log -L fails for new files, renamed functions, etc.
                return []

        except Exception:
            # Silently skip errors - not critical for indexing
            return []

        return commits

    def get_functions_evolution_batch(
        self,
        file_path: str,
        functions: list[dict],
    ) -> dict[str, dict | None]:
        """
        Get evolution metadata for multiple functions in a single file using batched git queries.

        This is much faster than calling get_function_evolution() for each function individually,
        as it makes a single git log call with multiple -L flags.

        Args:
            file_path: Relative path to file from repo root
            functions: List of function dicts with 'name' and optionally 'line' fields

        Returns:
            Dictionary mapping function_name -> evolution_dict (same format as get_function_evolution)
            Returns None for functions where git history lookup failed
        """
        if not functions:
            return {}

        results: dict[str, dict | None] = {}

        # Try function-based tracking first (requires .gitattributes or git built-in support)
        cmd = ["git", "log", "--format=%H|%an|%ae|%aI|%s", "--no-patch"]

        # Add -L flag for each function using function names
        for func in functions:
            func_name = func.get("name")
            if func_name:
                cmd.append(f"-L:{func_name}:{file_path}")

        try:
            # Run single batched command
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output - git log with multiple -L flags shows commits for each function
            # The output format is still one commit per line, but filtered to only show
            # commits that touched ANY of the specified functions
            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line or line.startswith("diff"):
                    continue

                parts = line.split("|")
                if len(parts) >= 5:
                    full_sha = parts[0]
                    message = parts[4]
                    pr_number = self._extract_pr_number(message)

                    commit_info: dict[str, str | int] = {
                        "sha": full_sha[:8],
                        "full_sha": full_sha,
                        "author": parts[1],
                        "author_email": parts[2],
                        "date": parts[3],
                        "summary": message,
                        "message": message,
                    }
                    if pr_number:
                        commit_info["pr"] = pr_number

                    commits.append(commit_info)

            # If we got commits, compute evolution for each function
            # Since we can't easily separate which commits belong to which function in batch mode,
            # we use the combined history as an approximation for all functions
            # This is a reasonable tradeoff for the massive speed improvement
            if commits:
                created_info = {
                    "sha": commits[-1]["sha"],
                    "full_sha": commits[-1]["full_sha"],
                    "date": commits[-1]["date"],
                    "author": commits[-1]["author"],
                    "author_email": commits[-1]["author_email"],
                    "message": commits[-1]["summary"],
                }
                if "pr" in commits[-1]:
                    created_info["pr"] = commits[-1]["pr"]

                last_modified_info = {
                    "sha": commits[0]["sha"],
                    "full_sha": commits[0]["full_sha"],
                    "date": commits[0]["date"],
                    "author": commits[0]["author"],
                    "author_email": commits[0]["author_email"],
                    "message": commits[0]["summary"],
                }
                if "pr" in commits[0]:
                    last_modified_info["pr"] = commits[0]["pr"]

                evolution = {
                    "created_at": created_info,
                    "last_modified": last_modified_info,
                    "total_modifications": len(commits),
                }

                # Apply same evolution to all functions (approximate but fast)
                for func in functions:
                    func_name = func.get("name")
                    if func_name:
                        results[func_name] = evolution
            else:
                # No commits found, return None for all functions
                for func in functions:
                    func_name = func.get("name")
                    if func_name:
                        results[func_name] = None

            return results

        except subprocess.CalledProcessError:
            # Function-based tracking failed - try line-based fallback
            # This happens when .gitattributes is not configured for Elixir

            # Silently fall back to line-based tracking
            # Note: Fallback happens when function-based tracking fails, which can occur even
            # with .gitattributes configured if any function in the batch doesn't match git history
            # (e.g., recently added functions, renamed functions, or git pattern matching issues)

            # Build fallback command with line numbers instead of function names
            cmd = ["git", "log", "--format=%H|%an|%ae|%aI|%s", "--no-patch"]

            for func in functions:
                func_line = func.get("line")
                if func_line:
                    # Use a range of 50 lines to capture the whole function
                    end_line = func_line + 50
                    cmd.append(f"-L{func_line},{end_line}:{file_path}")

            # Try line-based tracking
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Parse output
                commits = []
                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        if not line or line.startswith("diff"):
                            continue

                        parts = line.split("|")
                        if len(parts) >= 5:
                            full_sha = parts[0]
                            message = parts[4]
                            pr_number = self._extract_pr_number(message)

                            commit_info: dict[str, str | int] = {
                                "sha": full_sha[:8],
                                "full_sha": full_sha,
                                "author": parts[1],
                                "author_email": parts[2],
                                "date": parts[3],
                                "summary": message,
                                "message": message,
                            }
                            if pr_number:
                                commit_info["pr"] = pr_number

                            commits.append(commit_info)

                # Apply evolution data
                if commits:
                    created_info = {
                        "sha": commits[-1]["sha"],
                        "full_sha": commits[-1]["full_sha"],
                        "date": commits[-1]["date"],
                        "author": commits[-1]["author"],
                        "author_email": commits[-1]["author_email"],
                        "message": commits[-1]["summary"],
                    }
                    if "pr" in commits[-1]:
                        created_info["pr"] = commits[-1]["pr"]

                    last_modified_info = {
                        "sha": commits[0]["sha"],
                        "full_sha": commits[0]["full_sha"],
                        "date": commits[0]["date"],
                        "author": commits[0]["author"],
                        "author_email": commits[0]["author_email"],
                        "message": commits[0]["summary"],
                    }
                    if "pr" in commits[0]:
                        last_modified_info["pr"] = commits[0]["pr"]

                    evolution = {
                        "created_at": created_info,
                        "last_modified": last_modified_info,
                        "total_modifications": len(commits),
                    }

                    for func in functions:
                        func_name = func.get("name")
                        if func_name:
                            results[func_name] = evolution
                else:
                    for func in functions:
                        func_name = func.get("name")
                        if func_name:
                            results[func_name] = None

            except Exception:
                # Line-based tracking also failed
                for func in functions:
                    func_name = func.get("name")
                    if func_name:
                        results[func_name] = None

        except Exception:
            # Any other error - return None for all functions
            for func in functions:
                func_name = func.get("name")
                if func_name:
                    results[func_name] = None

        return results

    def get_function_evolution(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        function_name: str | None = None,
    ) -> dict | None:
        """
        Get evolution metadata for a function (creation, last modification, change count).

        Uses git log -L to track the complete history of a function and
        extract key lifecycle information.

        Args:
            file_path: Relative path to file from repo root
            start_line: Starting line number (optional, for line-based tracking)
            end_line: Ending line number (optional, for line-based tracking)
            function_name: Function name to track (e.g., "create_user")

        Returns:
            Dictionary with evolution information:
            - created_at: {sha, date, author, message} for first commit
            - last_modified: {sha, date, author, message} for most recent commit
            - total_modifications: Total number of commits that touched this function
            - modification_frequency: Average commits per month (if > 1 month of history)
            Returns None if no history found or on error.

        Note:
            - Provide either function_name OR (start_line, end_line)
        """
        try:
            # Get all commits that touched this function (no limit)
            commits = self.get_function_history_precise(
                file_path,
                start_line=start_line,
                end_line=end_line,
                function_name=function_name,
                max_commits=1000,  # Get all commits
            )

            if not commits:
                return None

            # Calculate evolution metadata
            created_at = commits[-1]  # Oldest commit (last in list)
            last_modified = commits[0]  # Most recent commit (first in list)
            total_modifications = len(commits)

            # Calculate modification frequency (commits per month)
            modification_frequency = None
            if len(commits) > 1:
                try:
                    from datetime import datetime

                    first_date = datetime.fromisoformat(created_at["date"])
                    last_date = datetime.fromisoformat(last_modified["date"])
                    days_between = (last_date - first_date).days

                    if days_between > 0:
                        months = days_between / 30.0
                        modification_frequency = (
                            total_modifications / months if months > 0 else total_modifications
                        )
                except Exception:
                    # If date parsing fails, skip frequency calculation
                    pass

            return {
                "created_at": {
                    "sha": created_at["sha"],
                    "full_sha": created_at["full_sha"],
                    "date": created_at["date"],
                    "author": created_at["author"],
                    "author_email": created_at["author_email"],
                    "message": created_at["summary"],
                },
                "last_modified": {
                    "sha": last_modified["sha"],
                    "full_sha": last_modified["full_sha"],
                    "date": last_modified["date"],
                    "author": last_modified["author"],
                    "author_email": last_modified["author_email"],
                    "message": last_modified["summary"],
                },
                "total_modifications": total_modifications,
                "modification_frequency": modification_frequency,
            }

        except Exception as e:
            print(f"Error getting function evolution for {file_path}: {e}")
            return None

    def get_function_history(self, file_path: str, start_line: int, end_line: int) -> list[dict]:
        """
        Get line-by-line authorship for a function using git blame.

        Shows who wrote each line of code, with consecutive lines by the
        same author grouped together for easier reading.

        Args:
            file_path: Relative path to file from repo root
            start_line: Starting line number of the function
            end_line: Ending line number of the function

        Returns:
            List of blame groups, each containing:
            - author: Author name
            - author_email: Author email
            - sha: Commit SHA (short)
            - full_sha: Full commit SHA
            - date: Commit date
            - line_start: First line number in this group
            - line_end: Last line number in this group
            - line_count: Number of consecutive lines by this author
            - lines: List of {number, content} for each line
        """
        blame_groups = []

        try:
            # Use git blame with line range
            cmd = [
                "git",
                "blame",
                f"-L{start_line},{end_line}",
                "--porcelain",  # Machine-readable format
                file_path,
            ]

            result = subprocess.run(
                cmd, cwd=str(self.repo_path), capture_output=True, text=True, check=True
            )

            # Parse porcelain format
            lines_data = []
            current_commit = {}
            # Cache commit metadata by SHA to handle repeated commits
            # Optimization: Pre-validate commits during caching to avoid validation in hot loop
            commit_cache = {}
            # Track which commits have all required fields (valid)
            valid_commits = set()

            for line in result.stdout.split("\n"):
                if not line:
                    continue

                # Commit SHA line (40 char hex)
                if len(line) >= 40 and line[0:40].isalnum():
                    parts = line.split()
                    if len(parts) >= 3:
                        sha = parts[0]
                        # Check if we've seen this commit before
                        if sha in commit_cache:
                            # Reuse cached metadata
                            current_commit = {
                                **commit_cache[sha],
                                "line_number": int(parts[2]),
                            }
                        else:
                            # New commit - initialize with SHA and line number
                            current_commit = {
                                "sha": sha[:8],
                                "full_sha": sha,
                                "line_number": int(parts[2]),
                            }
                # Author name
                elif line.startswith("author "):
                    current_commit["author"] = line[7:]
                # Author email
                elif line.startswith("author-mail "):
                    email = line[12:].strip("<>")
                    current_commit["author_email"] = email
                # Author time
                elif line.startswith("author-time "):
                    try:
                        timestamp = int(line[12:])
                        current_commit["date"] = datetime.fromtimestamp(timestamp).isoformat()
                    except (ValueError, OSError):
                        current_commit["date"] = line[12:]
                    # Cache this commit's metadata and validate (after we have all fields)
                    if "author" in current_commit and "author_email" in current_commit:
                        commit_cache[current_commit["full_sha"]] = {
                            "sha": current_commit["sha"],
                            "full_sha": current_commit["full_sha"],
                            "author": current_commit["author"],
                            "author_email": current_commit["author_email"],
                            "date": current_commit["date"],
                        }
                        # Mark as valid to avoid per-line validation in hot loop
                        valid_commits.add(current_commit["full_sha"])
                # Actual code line (starts with tab)
                elif line.startswith("\t"):
                    code_line = line[1:]  # Remove leading tab
                    # Use pre-validated commit check (optimized - no field iteration per line)
                    if current_commit.get("full_sha") in valid_commits:
                        line_info = {**current_commit, "content": code_line}
                        lines_data.append(line_info)

            # Group consecutive lines by same author and commit
            if lines_data:
                current_group = {
                    "author": lines_data[0]["author"],
                    "author_email": lines_data[0]["author_email"],
                    "sha": lines_data[0]["sha"],
                    "full_sha": lines_data[0]["full_sha"],
                    "date": lines_data[0]["date"],
                    "line_start": lines_data[0]["line_number"],
                    "line_end": lines_data[0]["line_number"],
                    "lines": [
                        {
                            "number": lines_data[0]["line_number"],
                            "content": lines_data[0]["content"],
                        }
                    ],
                }

                for line_info in lines_data[1:]:
                    # Same author and commit? Extend current group
                    if (
                        line_info["author"] == current_group["author"]
                        and line_info["sha"] == current_group["sha"]
                    ):
                        current_group["line_end"] = line_info["line_number"]
                        _ = current_group["lines"].append(
                            {
                                "number": line_info["line_number"],
                                "content": line_info["content"],
                            }
                        )
                    else:
                        # Different author/commit - save current group and start new one
                        current_group["line_count"] = len(current_group["lines"])
                        blame_groups.append(current_group)
                        current_group = {
                            "author": line_info["author"],
                            "author_email": line_info["author_email"],
                            "sha": line_info["sha"],
                            "full_sha": line_info["full_sha"],
                            "date": line_info["date"],
                            "line_start": line_info["line_number"],
                            "line_end": line_info["line_number"],
                            "lines": [
                                {
                                    "number": line_info["line_number"],
                                    "content": line_info["content"],
                                }
                            ],
                        }

                # Add the last group
                current_group["line_count"] = len(current_group["lines"])
                blame_groups.append(current_group)

        except subprocess.CalledProcessError:
            # Silently skip - git blame fails for new/modified files
            return []
        except Exception:
            # Silently skip errors - not critical for indexing
            return []

        return blame_groups

    def get_recent_commits(self, max_count: int = 20) -> list[dict]:
        """
        Get recent commits in the repository

        Args:
            max_count: Maximum number of commits to return

        Returns:
            List of recent commits with summary information
        """
        commits = []

        for commit in self.repo.iter_commits(max_count=max_count):
            # Try to get stats, but handle errors for initial/incomplete commits
            try:
                files_changed = len(commit.stats.files)
            except Exception:
                # Can't get stats (e.g., initial commit, shallow clone)
                files_changed = 0

            commits.append(
                {
                    "sha": commit.hexsha[:8],
                    "full_sha": commit.hexsha,
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.summary,
                    "files_changed": files_changed,
                }
            )

        return commits

    def get_commit_details(self, commit_sha: str) -> dict | None:
        """
        Get detailed information about a specific commit

        Args:
            commit_sha: Commit SHA (can be short or full)

        Returns:
            Detailed commit information or None if not found:
            - sha: Short SHA
            - full_sha: Full SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date
            - message: Full commit message
            - files_changed: List of files modified
            - insertions: Number of lines inserted
            - deletions: Number of lines deleted
        """
        try:
            commit = self.repo.commit(commit_sha)

            # Try to get stats, but handle errors for initial/incomplete commits
            try:
                files_changed = list(commit.stats.files.keys())
                insertions = commit.stats.total["insertions"]
                deletions = commit.stats.total["deletions"]
            except Exception:
                # Can't get stats (e.g., initial commit, shallow clone)
                files_changed = []
                insertions = 0
                deletions = 0

            return {
                "sha": commit.hexsha[:8],
                "full_sha": commit.hexsha,
                "author": str(commit.author),
                "author_email": commit.author.email,
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
            }
        except Exception as e:
            print(f"Error getting commit {commit_sha}: {e}")
            return None

    def search_commits(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search commit messages for a query string

        Args:
            query: Search term to find in commit messages
            max_results: Maximum results to return

        Returns:
            List of matching commits
        """
        results = []
        query_lower = query.lower()

        # Search through the last 500 commits
        for commit in self.repo.iter_commits(max_count=500):
            if query_lower in str(commit.message).lower():
                results.append(
                    {
                        "sha": commit.hexsha[:8],
                        "full_sha": commit.hexsha,
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                        "message": commit.summary,
                    }
                )

                if len(results) >= max_results:
                    break

        return results

    def get_file_history_filtered(
        self,
        file_path: str,
        max_commits: int = 10,
        since_date: datetime | None = None,
        until_date: datetime | None = None,
        author: str | None = None,
        min_changes: int = 0,
    ) -> list[dict]:
        """
        Get commit history for a file with advanced filtering options.

        Args:
            file_path: Relative path to file from repo root
            max_commits: Maximum number of commits to return
            since_date: Only include commits after this date
            until_date: Only include commits before this date
            author: Filter by author name (substring match, case-insensitive)
            min_changes: Minimum number of lines changed (insertions + deletions)

        Returns:
            List of commit information dictionaries with keys:
            - sha: Short commit SHA (8 chars)
            - full_sha: Full commit SHA
            - author: Author name
            - author_email: Author email
            - date: Commit date in ISO format
            - message: Full commit message
            - summary: First line of commit message
            - insertions: Number of lines inserted (if min_changes > 0)
            - deletions: Number of lines deleted (if min_changes > 0)
        """
        commits = []
        author_lower = author.lower() if author else None

        try:
            # Get commits that touched this file
            for commit in self.repo.iter_commits(paths=file_path):
                # Apply date filters
                commit_date = commit.committed_datetime.replace(tzinfo=None)
                if since_date and commit_date < since_date:
                    continue
                if until_date and commit_date > until_date:
                    continue

                # Apply author filter
                if author_lower and author_lower not in str(commit.author).lower():
                    continue

                # Apply min_changes filter if specified
                if min_changes > 0:
                    try:
                        # Get stats for this specific file in this commit
                        file_stats = commit.stats.files.get(file_path, {})
                        insertions = int(file_stats.get("insertions", 0)) if file_stats else 0  # type: ignore
                        deletions = int(file_stats.get("deletions", 0)) if file_stats else 0  # type: ignore
                        total_changes = insertions + deletions

                        if total_changes < min_changes:
                            continue
                    except Exception:
                        # If we can't get stats, skip the filter
                        pass

                # Build commit info
                commit_info: dict[str, Any] = {
                    "sha": commit.hexsha[:8],
                    "full_sha": commit.hexsha,
                    "author": str(commit.author),
                    "author_email": commit.author.email,
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                    "summary": commit.summary,
                }

                # Add change stats if min_changes was specified
                if min_changes > 0:
                    try:
                        file_stats = commit.stats.files.get(file_path, {})
                        # Type: ignore - file_stats is dict with string keys, values can be int
                        insertions = int(file_stats.get("insertions", 0)) if file_stats else 0  # type: ignore
                        deletions = int(file_stats.get("deletions", 0)) if file_stats else 0  # type: ignore
                        commit_info["insertions"] = insertions
                        commit_info["deletions"] = deletions
                    except Exception:
                        commit_info["insertions"] = 0
                        commit_info["deletions"] = 0

                commits.append(commit_info)

                if len(commits) >= max_commits:
                    break

        except Exception as e:
            print(f"Error getting filtered history for {file_path}: {e}")

        return commits


def main():
    """Test git helper functions"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m cicada.git_helper /path/to/repo")
        print("\nExample:")
        print("  python -m cicada.git_helper .")
        return

    repo_path = sys.argv[1]

    try:
        helper = GitHelper(repo_path)

        print("=" * 60)
        print("Git Helper Test")
        print("=" * 60)

        print("\n📋 Recent commits (last 5):")
        for commit in helper.get_recent_commits(5):
            print(f"  {commit['sha']} - {commit['message']}")
            print(f"    by {commit['author']} ({commit['files_changed']} files)")

        print("\n🔍 Searching for 'README' in commits:")
        for commit in helper.search_commits("README", 3):
            print(f"  {commit['sha']} - {commit['message']}")

        # Try to get history for a known file
        print("\n📁 Testing file history:")
        test_files = ["README.md", "pyproject.toml", "cicada/mcp_server.py"]
        for test_file in test_files:
            history = helper.get_file_history(test_file, max_commits=3)
            if history:
                print(f"\n  {test_file} (last 3 commits):")
                for commit in history:
                    print(f"    {commit['sha']} - {commit['summary']}")
                break

        print("\n✅ Git helper is working correctly!")

    except git.InvalidGitRepositoryError:
        print(f"❌ Error: {repo_path} is not a git repository")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
