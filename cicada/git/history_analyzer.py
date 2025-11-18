"""
Unified Git History Analyzer - consolidates git_blame, git_history, find_pr_for_line, and file_pr_history.

This module provides a single interface for all git history queries with smart routing
based on parameters and intelligent PR data fallback.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cicada.git import GitHelper
from cicada.github import PRFinder


class HistoryAnalyzer:
    """
    Unified analyzer for git history queries.

    Consolidates functionality from:
    - get_blame: Line-by-line authorship
    - get_commit_history: File/function evolution
    - find_pr_for_line: PR attribution for specific lines
    - get_file_pr_history: Complete PR history for files
    """

    # "Recent" means commits within the last N days
    DEFAULT_RECENT_DAYS = 14

    def __init__(
        self,
        repo_path: str,
        pr_index: dict[str, Any] | None = None,
        verbose: bool = False,
    ):
        """
        Initialize the history analyzer.

        Args:
            repo_path: Path to the git repository
            pr_index: Optional PR index for fast PR lookups
            verbose: Enable verbose logging
        """
        self.repo_path = Path(repo_path).resolve()
        self.pr_index = pr_index
        self.verbose = verbose

        # Initialize git helper
        self.git_helper = GitHelper(str(self.repo_path))

        # Initialize PR finder (with index if available)
        self.pr_finder: PRFinder | None
        try:
            from cicada.utils.storage import get_pr_index_path

            index_path = get_pr_index_path(self.repo_path)
            use_index = pr_index is not None or index_path.exists()

            self.pr_finder = PRFinder(
                repo_path=str(self.repo_path),
                use_index=use_index,
                index_path=str(index_path) if use_index else None,
                verbose=verbose,
            )
        except (ImportError, AttributeError) as e:
            # Expected failures - dependencies not available
            if self.verbose:
                print(f"Warning: PR finder dependencies not available: {e}")
            self.pr_finder = None
        except (OSError, ValueError) as e:
            # Expected failures - file system or path issues
            if self.verbose:
                print(f"Warning: Could not initialize PR finder due to path/file issue: {e}")
            self.pr_finder = None
        except Exception as e:
            # Unexpected failure - log and re-raise in verbose mode for debugging
            error_msg = f"Unexpected error initializing PR finder: {e}"
            if self.verbose:
                print(f"ERROR: {error_msg}")
                import traceback

                traceback.print_exc()
            # Still set to None to allow operation without PR enrichment
            self.pr_finder = None

    def _parse_recent_filter(self, recent: bool | None) -> tuple[datetime | None, datetime | None]:
        """
        Convert recent filter to date range.

        Args:
            recent: True (last DEFAULT_RECENT_DAYS), False (older than DEFAULT_RECENT_DAYS),
                   None (all time)

        Returns:
            Tuple of (since_date, until_date)
        """
        if recent is None:
            return None, None

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.DEFAULT_RECENT_DAYS)

        if recent:
            # Last N days: since=cutoff, until=None
            return cutoff, None
        else:
            # Older than N days: since=None, until=cutoff
            return None, cutoff

    def _filter_by_date(
        self,
        date_str: str,
        since_date: datetime | None,
        until_date: datetime | None,
    ) -> bool:
        """
        Check if a date falls within the specified range.

        Args:
            date_str: ISO format date string
            since_date: Optional minimum date (inclusive)
            until_date: Optional maximum date (inclusive)

        Returns:
            True if date is within range, False otherwise
        """
        if not (since_date or until_date):
            return True

        try:
            commit_date = datetime.fromisoformat(date_str)
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)

            if since_date and commit_date < since_date:
                return False
            return not (until_date and commit_date > until_date)
        except Exception as e:
            # Log error in verbose mode
            if self.verbose:
                print(f"Warning: Could not parse date '{date_str}': {e}")
            return True  # Don't filter on parsing errors

    def analyze(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        function_name: str | None = None,
        show_evolution: bool = False,
        max_results: int = 10,
        recent: bool | None = None,
        author: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze git history based on parameters - smart routing to appropriate method.

        Args:
            file_path: Path to file (relative to repo root)
            start_line: Optional line number (single line) or range start
            end_line: Optional range end
            function_name: Optional function name for tracking
            show_evolution: Include creation/modification metadata
            max_results: Maximum commits/PRs to return
            recent: True (last 14 days), False (older), None (all time)
            author: Filter by author name

        Returns:
            Dictionary with:
                - type: "single_line" | "line_range" | "function" | "file"
                - data: Formatted result data
                - pr_enriched: Whether PR data was included
        """
        # Convert recent filter to date range
        since_date, until_date = self._parse_recent_filter(recent)

        # Route to appropriate analyzer method
        if start_line is not None and end_line is None:
            # Single line - blame + find PR
            return self._analyze_single_line(file_path, start_line)

        elif start_line is not None and end_line is not None:
            # Line range - blame with optional PR enrichment
            return self._analyze_line_range(
                file_path, start_line, end_line, max_results, since_date, until_date, author
            )

        elif function_name is not None:
            # Function tracking
            return self._analyze_function(
                file_path,
                function_name,
                start_line,
                end_line,
                show_evolution,
                max_results,
                since_date,
                until_date,
                author,
            )

        else:
            # File-level - try PRs first, fallback to commits
            return self._analyze_file(
                file_path, max_results, since_date, until_date, author, show_evolution
            )

    def _analyze_single_line(self, file_path: str, line_number: int) -> dict[str, Any]:
        """
        Analyze a single line - find author and associated PR.

        Args:
            file_path: Path to file
            line_number: Line number (1-indexed)

        Returns:
            Dictionary with blame info and PR data
        """
        # Get blame info
        blame_groups = self.git_helper.get_function_history(file_path, line_number, line_number)

        if not blame_groups or len(blame_groups) == 0:
            return {
                "type": "single_line",
                "data": None,
                "pr_enriched": False,
                "error": f"No blame information for line {line_number}",
            }

        # Should only be one group for a single line
        blame = blame_groups[0]

        # Try to find associated PR
        pr_info = None
        if self.pr_finder:
            try:
                result = self.pr_finder.find_pr_for_line(file_path, line_number)
                pr_info = result.get("pr")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not find PR for line: {e}")

        return {
            "type": "single_line",
            "data": {
                "file_path": file_path,
                "line_number": line_number,
                "author": blame["author"],
                "author_email": blame["author_email"],
                "sha": blame["sha"],
                "full_sha": blame["full_sha"],
                "date": blame["date"],
                "lines": blame.get("lines", []),
                "pr": pr_info,
            },
            "pr_enriched": pr_info is not None,
        }

    def _analyze_line_range(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        max_results: int,
        since_date: datetime | None,
        until_date: datetime | None,
        author: str | None,
    ) -> dict[str, Any]:
        """
        Analyze a line range - blame groups with optional PR enrichment.

        Args:
            file_path: Path to file
            start_line: Starting line
            end_line: Ending line
            max_results: Maximum blame groups to return
            since_date: Optional date filter (only commits after)
            until_date: Optional date filter (only commits before)
            author: Optional author filter

        Returns:
            Dictionary with grouped blame info and PR enrichment
        """
        # Get blame groups
        blame_groups = self.git_helper.get_function_history(file_path, start_line, end_line)

        if not blame_groups:
            return {
                "type": "line_range",
                "data": None,
                "pr_enriched": False,
                "error": f"No blame information for lines {start_line}-{end_line}",
            }

        # Apply filters
        filtered_groups = []
        for group in blame_groups:
            # Date filter
            if not self._filter_by_date(group["date"], since_date, until_date):
                continue

            # Author filter
            if author and author.lower() not in group["author"].lower():
                continue

            filtered_groups.append(group)

        # Limit results
        filtered_groups = filtered_groups[:max_results]

        # Try to enrich with PR data
        pr_enriched = False
        if self.pr_finder and self.pr_index:
            commit_to_pr = self.pr_index.get("commit_to_pr", {})
            prs_data = self.pr_index.get("prs", {})

            for group in filtered_groups:
                commit_sha = group["full_sha"]
                pr_number = commit_to_pr.get(commit_sha)

                if pr_number:
                    pr = prs_data.get(str(pr_number))
                    if pr:
                        group["pr"] = {
                            "number": pr["number"],
                            "title": pr["title"],
                            "author": pr.get("author", "unknown"),
                            "status": pr.get("status", "unknown"),
                            "merged": pr.get("merged", False),
                            "url": pr.get("url", ""),
                        }
                        pr_enriched = True

        return {
            "type": "line_range",
            "data": {
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "groups": filtered_groups,
            },
            "pr_enriched": pr_enriched,
        }

    def _analyze_function(
        self,
        file_path: str,
        function_name: str,
        start_line: int | None,
        end_line: int | None,
        show_evolution: bool,
        max_results: int,
        since_date: datetime | None,
        until_date: datetime | None,
        author: str | None,
    ) -> dict[str, Any]:
        """
        Analyze function evolution using git log -L.

        Args:
            file_path: Path to file
            function_name: Function name to track
            start_line: Optional fallback line start
            end_line: Optional fallback line end
            show_evolution: Include creation/modification metadata
            max_results: Maximum commits to return
            since_date: Optional date filter
            until_date: Optional date filter
            author: Optional author filter

        Returns:
            Dictionary with function history and evolution data
        """
        # Get function history
        commits = self.git_helper.get_function_history_precise(
            file_path,
            start_line=start_line,
            end_line=end_line,
            function_name=function_name,
            max_commits=max_results,
        )

        if not commits:
            return {
                "type": "function",
                "data": None,
                "pr_enriched": False,
                "error": f"No history found for function {function_name}",
            }

        # Apply filters (note: git log -L doesn't support these natively)
        filtered_commits = []
        for commit in commits:
            # Date filter
            if not self._filter_by_date(commit["date"], since_date, until_date):
                continue

            # Author filter
            if author and author.lower() not in commit["author"].lower():
                continue

            filtered_commits.append(commit)

        # Get evolution metadata if requested
        evolution = None
        if show_evolution:
            evolution = self.git_helper.get_function_evolution(
                file_path,
                start_line=start_line,
                end_line=end_line,
                function_name=function_name,
            )

        return {
            "type": "function",
            "data": {
                "file_path": file_path,
                "function_name": function_name,
                "commits": filtered_commits,
                "evolution": evolution,
            },
            "pr_enriched": False,  # Function tracking doesn't include PR enrichment
        }

    def _analyze_file(
        self,
        file_path: str,
        max_results: int,
        since_date: datetime | None,
        until_date: datetime | None,
        author: str | None,
        show_evolution: bool,
    ) -> dict[str, Any]:
        """
        Analyze file-level history - try PRs first, fallback to commits.

        Args:
            file_path: Path to file
            max_results: Maximum results to return
            since_date: Optional date filter
            until_date: Optional date filter
            author: Optional author filter
            show_evolution: Include evolution metadata

        Returns:
            Dictionary with file history (PRs preferred, commits fallback)
        """
        # Try PR index first (fast, rich data)
        if self.pr_index:
            pr_data = self._get_file_pr_history(
                file_path, max_results, since_date, until_date, author
            )
            if pr_data:
                return {
                    "type": "file",
                    "data": pr_data,
                    "pr_enriched": True,
                }

        # Fallback to commit history
        has_filters = since_date or until_date or author
        if has_filters:
            commits = self.git_helper.get_file_history_filtered(
                file_path,
                max_commits=max_results,
                since_date=since_date,
                until_date=until_date,
                author=author,
                min_changes=0,
            )
        else:
            commits = self.git_helper.get_file_history(file_path, max_results)

        return {
            "type": "file",
            "data": {
                "file_path": file_path,
                "commits": commits,
            },
            "pr_enriched": False,
        }

    def _get_file_pr_history(
        self,
        file_path: str,
        max_results: int,
        since_date: datetime | None,
        until_date: datetime | None,
        author: str | None,
    ) -> dict[str, Any] | None:
        """
        Get PR history for a file from the index.

        Args:
            file_path: Path to file
            max_results: Maximum PRs to return
            since_date: Optional date filter
            until_date: Optional date filter
            author: Optional author filter

        Returns:
            Dictionary with PR history or None if not available
        """
        if not self.pr_index:
            return None

        file_to_prs = self.pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path, [])

        if not pr_numbers:
            return None

        prs_data = self.pr_index.get("prs", {})
        prs = []

        for pr_num in pr_numbers:
            pr = prs_data.get(str(pr_num))
            if not pr:
                continue

            # Apply filters
            # Date filter (use PR merged_at or created_at)
            pr_date_str = pr.get("merged_at") or pr.get("created_at")
            if pr_date_str:
                # Normalize GitHub's Z suffix to +00:00 for ISO parsing
                pr_date_str = pr_date_str.replace("Z", "+00:00")
                if not self._filter_by_date(pr_date_str, since_date, until_date):
                    continue

            # Author filter
            if author and author.lower() not in pr.get("author", "").lower():
                continue

            # Get comments for this file
            comments = pr.get("comments", [])
            file_comments = [c for c in comments if c.get("path") == file_path]

            prs.append(
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "author": pr.get("author", "unknown"),
                    "status": pr.get("status", "unknown"),
                    "merged": pr.get("merged", False),
                    "created_at": pr.get("created_at"),
                    "merged_at": pr.get("merged_at"),
                    "url": pr.get("url", ""),
                    "description": pr.get("description", ""),
                    "comments": file_comments,
                }
            )

            if len(prs) >= max_results:
                break

        if not prs:
            return None

        return {"file_path": file_path, "prs": prs}

    def format_result(self, result: dict[str, Any]) -> str:
        """
        Format analysis result as markdown.

        Args:
            result: Result from analyze() method

        Returns:
            Formatted markdown string
        """
        result_type = result["type"]
        data = result["data"]

        if data is None:
            error = result.get("error", "No data available")
            return f"**Error:** {error}"

        if result_type == "single_line":
            return self._format_single_line(data)
        elif result_type == "line_range":
            return self._format_line_range(data)
        elif result_type == "function":
            return self._format_function(data)
        elif result_type == "file":
            return self._format_file(data, result["pr_enriched"])
        else:
            return f"**Unknown result type:** {result_type}"

    def _format_single_line(self, data: dict[str, Any]) -> str:
        """Format single line result."""
        lines = [
            f"## Line {data['line_number']} in {data['file_path']}",
            "",
            f"**Author:** {data['author']} ({data['date'][:10]}, {data['sha']})",
        ]

        # Add PR info if available
        pr = data.get("pr")
        if pr:
            pr_status = "merged" if pr.get("merged") else pr.get("state", "unknown")
            lines.append(
                f"**PR:** [#{pr['number']}]({pr['url']}) - {pr['title']} (@{pr['author']}, {pr_status})"
            )
        else:
            lines.append("**PR:** None")

        # Add code snippet if available
        code_lines = data.get("lines", [])
        if code_lines:
            lines.append("")
            lines.append("```")
            for line in code_lines[:5]:  # Limit to 5 lines
                lines.append(line["content"])
            lines.append("```")

        return "\n".join(lines)

    def _format_line_range(self, data: dict[str, Any]) -> str:
        """Format line range result."""
        lines = [
            f"## Lines {data['start_line']}-{data['end_line']} in {data['file_path']}",
            "",
        ]

        groups = data.get("groups", [])
        for group in groups:
            line_range = (
                f"{group['line_start']}-{group['line_end']}"
                if group["line_start"] != group["line_end"]
                else str(group["line_start"])
            )

            lines.append(
                f"### Lines {line_range} ({group['sha']}, {group['author']}, {group['date'][:10]})"
            )

            # Show code snippet (limit to avoid huge output)
            code_lines = group.get("lines", [])
            if code_lines:
                lines.append("```")
                # Show first 5 and last 5 if more than 10 lines
                if len(code_lines) > 10:
                    for line in code_lines[:5]:
                        lines.append(line["content"])
                    lines.append("...")
                    for line in code_lines[-5:]:
                        lines.append(line["content"])
                else:
                    for line in code_lines:
                        lines.append(line["content"])
                lines.append("```")

            # Show PR if available
            pr = group.get("pr")
            if pr:
                pr_status = "merged" if pr.get("merged") else pr.get("status", "unknown")
                lines.append(
                    f"**PR:** [#{pr['number']}]({pr['url']}) - {pr['title']} (@{pr['author']}, {pr_status})"
                )

            lines.append("")

        return "\n".join(lines)

    def _format_function(self, data: dict[str, Any]) -> str:
        """Format function history result."""
        lines = [
            f"## Function {data['function_name']} in {data['file_path']}",
            "",
        ]

        # Add evolution metadata if available
        evolution = data.get("evolution")
        if evolution:
            created = evolution["created_at"]
            last_mod = evolution["last_modified"]
            total_mods = evolution["total_modifications"]
            freq = evolution.get("modification_frequency")

            lines.append("### Evolution")
            lines.append(
                f"- **Created:** {created['date'][:10]} ({created['sha']}, {created['author']})"
            )
            lines.append(
                f"- **Last modified:** {last_mod['date'][:10]} ({last_mod['sha']}, {last_mod['author']})"
            )
            lines.append(f"- **Total modifications:** {total_mods}")
            if freq:
                lines.append(f"- **Frequency:** {freq:.1f} commits/month")
            lines.append("")

        # Add recent commits
        commits = data.get("commits", [])
        if commits:
            lines.append("### Recent Commits")
            for commit in commits:
                lines.append(
                    f"- **{commit['sha']}** ({commit['date'][:10]}) {commit['author']}: {commit['summary']}"
                )

        return "\n".join(lines)

    def _format_file(self, data: dict[str, Any], pr_enriched: bool) -> str:
        """Format file history result."""
        file_path = data["file_path"]
        lines = [f"## History for {file_path}", ""]

        if pr_enriched:
            # Format PR history
            prs = data.get("prs", [])
            for pr in prs:
                pr_status = "merged" if pr.get("merged") else pr.get("status", "unknown")
                date = pr.get("merged_at") or pr.get("created_at", "")
                date_str = date[:10] if date else "unknown"

                lines.append(f"### PR #{pr['number']}: {pr['title']} ({pr_status}, {date_str})")
                lines.append(f"**Author:** @{pr['author']}")
                lines.append(f"**URL:** {pr['url']}")

                # Show description (truncated)
                description = pr.get("description", "")
                if description:
                    desc_lines = description.split("\n")
                    if len(desc_lines) > 10:
                        lines.append("")
                        lines.extend(desc_lines[:10])
                        lines.append("*(truncated)*")
                    else:
                        lines.append("")
                        lines.extend(desc_lines)

                # Show comments
                comments = pr.get("comments", [])
                if comments:
                    lines.append("")
                    lines.append("**Review comments:**")
                    for comment in comments[:5]:  # Limit to 5 comments
                        line_num = comment.get("line")
                        author = comment.get("author", "unknown")
                        body = comment.get("body", "")
                        resolved = " (resolved)" if comment.get("resolved") else ""
                        lines.append(f"> Line {line_num} ({author}{resolved}): {body[:100]}")

                lines.append("")
                lines.append("---")
                lines.append("")

        else:
            # Format commit history
            commits = data.get("commits", [])
            for commit in commits:
                lines.append(f"### {commit['sha']} ({commit['date'][:10]}) - {commit['author']}")
                lines.append(f"{commit['summary']}")
                lines.append("")

        return "\n".join(lines)
