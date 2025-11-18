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
        self.pr_finder: PRFinder | None = self._init_pr_finder()

    def _init_pr_finder(self) -> PRFinder | None:
        """Best-effort PR finder initialization with compact logging."""
        try:
            from cicada.utils.storage import get_pr_index_path
        except (ImportError, AttributeError) as exc:
            if self.verbose:
                print(f"Warning: PR finder dependencies not available: {exc}")
            return None

        index_path = get_pr_index_path(self.repo_path)
        use_index = self.pr_index is not None or index_path.exists()

        try:
            return PRFinder(
                repo_path=str(self.repo_path),
                use_index=use_index,
                index_path=str(index_path) if use_index else None,
                verbose=self.verbose,
            )
        except (OSError, ValueError) as exc:
            if self.verbose:
                print(f"Warning: Could not initialize PR finder due to path/file issue: {exc}")
            return None
        except Exception as exc:
            if self.verbose:
                print(f"ERROR: Unexpected error initializing PR finder: {exc}")
                import traceback

                traceback.print_exc()
            return None

    def _parse_recent_filter(self, recent: bool | None) -> tuple[datetime | None, datetime | None]:
        """Convert the recent flag to a (since, until) tuple."""
        if recent is None:
            return None, None

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.DEFAULT_RECENT_DAYS)
        return (cutoff, None) if recent else (None, cutoff)

    def _filter_by_date(
        self,
        date_str: str,
        since_date: datetime | None,
        until_date: datetime | None,
    ) -> bool:
        if not (since_date or until_date):
            return True

        try:
            commit_date = datetime.fromisoformat(date_str)
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)

            too_early = since_date and commit_date < since_date
            too_late = until_date and commit_date > until_date
            return not (too_early or too_late)
        except Exception as exc:
            if self.verbose:
                print(f"Warning: Could not parse date '{date_str}': {exc}")
            return True  # Don't filter on parsing errors

    @staticmethod
    def _author_matches(target: str | None, author: str | None) -> bool:
        return not author or author.lower() in (target or "").lower()

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
        since_date, until_date = self._parse_recent_filter(recent)

        if start_line is not None and end_line is None:
            return self._analyze_single_line(file_path, start_line)
        if start_line is not None and end_line is not None:
            return self._analyze_line_range(
                file_path,
                start_line,
                end_line,
                max_results,
                since_date,
                until_date,
                author,
            )
        if function_name is not None:
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
        blame_groups = self.git_helper.get_function_history(file_path, line_number, line_number)
        if not blame_groups:
            return {
                "type": "single_line",
                "data": None,
                "pr_enriched": False,
                "error": f"No blame information for line {line_number}",
            }

        blame = blame_groups[0]

        pr_info = None
        if self.pr_finder:
            try:
                pr_info = (self.pr_finder.find_pr_for_line(file_path, line_number) or {}).get("pr")
            except Exception as exc:
                if self.verbose:
                    print(f"Warning: Could not find PR for line: {exc}")

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
        blame_groups = self.git_helper.get_function_history(file_path, start_line, end_line)

        if not blame_groups:
            return {
                "type": "line_range",
                "data": None,
                "pr_enriched": False,
                "error": f"No blame information for lines {start_line}-{end_line}",
            }

        filtered_groups = [
            group
            for group in blame_groups
            if self._filter_by_date(group["date"], since_date, until_date)
            and self._author_matches(group["author"], author)
        ][:max_results]

        # Try to enrich with PR data
        pr_enriched = False
        if self.pr_finder and self.pr_index:
            commit_to_pr = self.pr_index.get("commit_to_pr", {})
            prs_data = self.pr_index.get("prs", {})

            for group in filtered_groups:
                pr_number = commit_to_pr.get(group["full_sha"])
                if not pr_number:
                    continue

                pr = prs_data.get(str(pr_number))
                if not pr:
                    continue

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

        filtered_commits = [
            commit
            for commit in commits
            if self._filter_by_date(commit["date"], since_date, until_date)
            and self._author_matches(commit["author"], author)
        ]

        evolution = (
            self.git_helper.get_function_evolution(
                file_path,
                start_line=start_line,
                end_line=end_line,
                function_name=function_name,
            )
            if show_evolution
            else None
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
        pr_data = (
            self._get_file_pr_history(file_path, max_results, since_date, until_date, author)
            if self.pr_index
            else None
        )
        if pr_data:
            return {"type": "file", "data": pr_data, "pr_enriched": True}

        has_filters = since_date or until_date or author
        commits = (
            self.git_helper.get_file_history_filtered(
                file_path,
                max_commits=max_results,
                since_date=since_date,
                until_date=until_date,
                author=author,
                min_changes=0,
            )
            if has_filters
            else self.git_helper.get_file_history(file_path, max_results)
        )

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

        pr_numbers = self.pr_index.get("file_to_prs", {}).get(file_path, [])
        prs_data = self.pr_index.get("prs", {})
        prs: list[dict[str, Any]] = []

        for pr_num in pr_numbers:
            if len(prs) >= max_results:
                break

            pr = prs_data.get(str(pr_num))
            if not pr:
                continue

            pr_date_str = (pr.get("merged_at") or pr.get("created_at") or "").replace("Z", "+00:00")
            if pr_date_str and not self._filter_by_date(pr_date_str, since_date, until_date):
                continue
            if not self._author_matches(pr.get("author", ""), author):
                continue

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

        formatter_map = {
            "single_line": self._format_single_line,
            "line_range": self._format_line_range,
            "function": self._format_function,
        }

        if result_type == "file":
            return self._format_file(data, result["pr_enriched"])

        formatter = formatter_map.get(result_type)
        return formatter(data) if formatter else f"**Unknown result type:** {result_type}"

    @staticmethod
    def _append_code_block(
        lines: list[str], code_lines: list[dict[str, Any]], allow_long: bool = False
    ) -> None:
        if not code_lines:
            return

        lines.append("```")
        if allow_long and len(code_lines) > 10:
            lines.extend(line["content"] for line in code_lines[:5])
            lines.append("...")
            lines.extend(line["content"] for line in code_lines[-5:])
        else:
            lines.extend(line["content"] for line in (code_lines if allow_long else code_lines[:5]))
        lines.append("```")

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
            self._append_code_block(lines, code_lines)

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
                self._append_code_block(lines, code_lines, allow_long=True)

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

        if not pr_enriched:
            for commit in data.get("commits", []):
                lines.append(f"### {commit['sha']} ({commit['date'][:10]}) - {commit['author']}")
                lines.append(f"{commit['summary']}")
                lines.append("")
            return "\n".join(lines)

        for pr in data.get("prs", []):
            pr_status = "merged" if pr.get("merged") else pr.get("status", "unknown")
            date = pr.get("merged_at") or pr.get("created_at", "")
            date_str = date[:10] if date else "unknown"

            lines.append(f"### PR #{pr['number']}: {pr['title']} ({pr_status}, {date_str})")
            lines.append(f"**Author:** @{pr['author']}")
            lines.append(f"**URL:** {pr['url']}")

            description = pr.get("description", "")
            if description:
                desc_lines = description.split("\n")
                lines.append("")
                lines.extend(desc_lines[:10])
                if len(desc_lines) > 10:
                    lines.append("*(truncated)*")

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

        return "\n".join(lines)
