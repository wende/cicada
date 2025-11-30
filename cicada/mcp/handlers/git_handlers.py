"""
Git History Tool Handlers.

Handles tools for git history, blame, and commit information.
"""

import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.types import TextContent

from cicada.git import GitHelper
from cicada.git.formatter import GitFormatter


class GitHistoryHandler:
    """Handler for git history-related tools."""

    def __init__(self, git_helper: GitHelper | None, config: dict[str, Any]):
        """
        Initialize the git history handler.

        Args:
            git_helper: GitHelper instance, or None if git is not available
            config: Configuration dictionary
        """
        self.git_helper = git_helper
        self.config = config

    def parse_changed_since(self, changed_since: str) -> datetime:
        """
        Parse changed_since parameter into datetime.

        Supports:
        - ISO dates: '2024-01-15'
        - Relative: '7d', '2w', '3m', '1y'
        - Git refs: 'HEAD~10', 'v1.0.0' (if git_helper available)

        Returns:
            datetime object (timezone-aware) representing the cutoff date

        Raises:
            ValueError: If format is invalid or amount is negative/zero
        """
        # ISO date format (YYYY-MM-DD)
        if "-" in changed_since and len(changed_since) >= 10:
            try:
                dt = datetime.fromisoformat(changed_since)
                # Ensure timezone-aware - if naive, assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass

        # Relative format (7d, 2w, 3m, 1y)
        if len(changed_since) >= 2 and changed_since[-1] in "dwmy":
            try:
                amount = int(changed_since[:-1])
                unit = changed_since[-1]

                # Validate positive amount
                if amount <= 0:
                    raise ValueError(f"Time amount must be positive, got: {amount}{unit}")

                now = datetime.now(timezone.utc)
                if unit == "d":
                    return now - timedelta(days=amount)
                elif unit == "w":
                    return now - timedelta(weeks=amount)
                elif unit == "m":
                    return now - timedelta(days=amount * 30)
                elif unit == "y":
                    return now - timedelta(days=amount * 365)
            except ValueError as e:
                # Re-raise if it's our validation error
                if "Time amount must be positive" in str(e):
                    raise
                # Otherwise, try next format (likely invalid int parsing)

        # Git ref format (requires git_helper)
        if self.git_helper:
            try:
                # Validate git ref format to prevent command injection
                # Refs should not start with - or -- (could be flags)
                if changed_since.startswith("-"):
                    raise ValueError(f"Invalid git ref format (starts with '-'): {changed_since}")

                # Get timestamp of the ref using git show
                repo_path = self.git_helper.repo_path
                result = subprocess.run(
                    ["git", "show", "-s", "--format=%ai", changed_since],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                dt = datetime.fromisoformat(result.stdout.strip())
                # Git returns timezone-aware datetime, ensure it has tzinfo
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except subprocess.CalledProcessError:
                # Git command failed - invalid ref or other git error
                pass
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception:
                # Other errors (e.g., datetime parsing) - try next format
                pass

        raise ValueError(f"Invalid changed_since format: {changed_since}")

    async def get_file_history(
        self,
        file_path: str,
        function_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        show_evolution: bool = False,
        max_commits: int = 10,
        since_date: str | None = None,
        until_date: str | None = None,
        author: str | None = None,
        min_changes: int = 0,
    ) -> list[TextContent]:
        """
        Get git commit history for a file or function.

        Args:
            file_path: Path to the file
            function_name: Optional function name for function tracking (git log -L :funcname:file)
            start_line: Optional starting line for fallback line-based tracking
            end_line: Optional ending line for fallback line-based tracking
            show_evolution: Include function evolution metadata
            max_commits: Maximum number of commits to return
            since_date: Only include commits after this date (ISO format or relative like '7d', '2w')
            until_date: Only include commits before this date (ISO format or relative)
            author: Filter by author name (substring match)
            min_changes: Minimum number of lines changed

        Returns:
            TextContent with formatted commit history

        Note:
            - If function_name is provided, uses git's function tracking
            - Function tracking works even as the function moves in the file
            - Line numbers are used as fallback if function tracking fails
            - Requires .gitattributes with "*.ex diff=elixir" for function tracking
            - Date filters only work with file-level history (not function/line tracking)
        """
        if not self.git_helper:
            error_msg = "Git history is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

        # Parse date filters if provided
        since_datetime = None
        until_datetime = None
        if since_date:
            since_datetime = self.parse_changed_since(since_date)
        if until_date:
            until_datetime = self.parse_changed_since(until_date)

        # Check if any filters are being used (only supported for file-level history)
        has_filters = since_date or until_date or author or min_changes > 0
        if has_filters and (function_name or (start_line and end_line)):
            warning_msg = "WARNING: Date/author/min_changes filters only work with file-level history (without function_name or line range)\n\n"
        else:
            warning_msg = ""

        try:
            evolution = None
            tracking_method = "file"

            # Determine which tracking method to use
            # Priority: function name > line numbers > file level
            if function_name:
                # Use function-based tracking (git log -L :funcname:file)
                commits = self.git_helper.get_function_history_precise(
                    file_path,
                    start_line=start_line,
                    end_line=end_line,
                    function_name=function_name,
                    max_commits=max_commits,
                )
                tracking_method = "function"

                # Get evolution metadata if requested
                if show_evolution:
                    evolution = self.git_helper.get_function_evolution(
                        file_path,
                        start_line=start_line,
                        end_line=end_line,
                        function_name=function_name,
                    )

            elif start_line and end_line:
                # Use line-based tracking (git log -L start,end:file)
                commits = self.git_helper.get_function_history_precise(
                    file_path,
                    start_line=start_line,
                    end_line=end_line,
                    max_commits=max_commits,
                )
                tracking_method = "line"

                if show_evolution:
                    evolution = self.git_helper.get_function_evolution(
                        file_path, start_line=start_line, end_line=end_line
                    )
            else:
                # File-level history
                if has_filters:
                    commits = self.git_helper.get_file_history_filtered(
                        file_path,
                        max_commits=max_commits,
                        since_date=since_datetime,
                        until_date=until_datetime,
                        author=author,
                        min_changes=min_changes,
                    )
                else:
                    commits = self.git_helper.get_file_history(file_path, max_commits)

            if not commits:
                result = f"No commit history found for {file_path}"
                return [TextContent(type="text", text=result)]

            # Build filter info string
            filter_info = ""
            if has_filters and not (function_name or (start_line and end_line)):
                filter_parts = []
                if since_date:
                    filter_parts.append(f"since {since_date}")
                if until_date:
                    filter_parts.append(f"until {until_date}")
                if author:
                    filter_parts.append(f"author: {author}")
                if min_changes > 0:
                    filter_parts.append(f"min changes: {min_changes}")
                filter_info = f"Filters: {', '.join(filter_parts)}"

            # Use centralized formatter
            result = GitFormatter.format_file_history(
                file_path=file_path,
                commits=commits,
                function_name=function_name,
                start_line=start_line,
                end_line=end_line,
                evolution=evolution,
                tracking_method=tracking_method,
                warning_msg=warning_msg,
                filter_info=filter_info,
            )
            return [TextContent(type="text", text=result)]

        except Exception as e:
            error_msg = f"Error getting file history: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def get_function_blame(
        self, file_path: str, start_line: int, end_line: int
    ) -> list[TextContent]:
        """
        Get line-by-line authorship for a code section using git blame.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            TextContent with formatted blame information
        """
        if not self.git_helper:
            error_msg = "Git blame is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

        try:
            blame_groups = self.git_helper.get_function_history(file_path, start_line, end_line)

            if not blame_groups:
                result = f"No blame information found for {file_path} lines {start_line}-{end_line}"
                return [TextContent(type="text", text=result)]

            # Use centralized formatter
            result = GitFormatter.format_blame(file_path, start_line, end_line, blame_groups)
            return [TextContent(type="text", text=result)]

        except Exception as e:
            error_msg = f"Error getting blame information: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def git_history(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        function_name: str | None = None,
        show_evolution: bool = False,
        max_results: int = 10,
        recent: bool | None = None,
        recent_days: int | None = None,
        author: str | None = None,
        include_pr_description: bool = False,
        include_review_comments: bool = False,
        verbose: bool = False,
    ) -> list[TextContent]:
        """
        Unified git history tool - consolidates get_blame, get_commit_history, find_pr_for_line, and get_file_pr_history.

        Args:
            file_path: Path to the file
            start_line: Optional line number or range start
            end_line: Optional range end
            function_name: Optional function name for tracking
            show_evolution: Include evolution metadata
            max_results: Maximum results to return
            recent: True (last N days), False (older), None (all time)
            recent_days: Number of days for recent filter (default: 14)
            author: Filter by author name
            include_pr_description: Include PR descriptions in output
            include_review_comments: Include PR review comments in output
            verbose: Enable verbose output (includes all details)

        Returns:
            TextContent with formatted history
        """
        if not self.git_helper:
            error_msg = "Git history is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

        try:
            # Get repo path and PR index from config
            from cicada.git import HistoryAnalyzer

            repo_path = self.config.get("repository", {}).get("path", ".")

            # Try to load PR index
            pr_index = None
            try:
                from cicada.utils import load_index
                from cicada.utils.storage import get_pr_index_path

                pr_index_path = get_pr_index_path(repo_path)
                if pr_index_path.exists():
                    pr_index = load_index(pr_index_path, verbose=False, raise_on_error=False)
            except Exception:
                pass  # PR index not available

            # Initialize HistoryAnalyzer
            analyzer = HistoryAnalyzer(repo_path=repo_path, pr_index=pr_index, verbose=False)

            # Perform analysis
            result = analyzer.analyze(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                function_name=function_name,
                show_evolution=show_evolution,
                max_results=max_results,
                recent=recent,
                recent_days=recent_days,
                author=author,
            )

            # Format result with compaction options
            format_opts = {
                "include_pr_description": include_pr_description or verbose,
                "include_review_comments": include_review_comments or verbose,
            }
            formatted = analyzer.format_result(result, format_opts)

            return [TextContent(type="text", text=formatted)]

        except Exception as e:
            error_msg = f"Error analyzing git history: {str(e)}"
            return [TextContent(type="text", text=error_msg)]
