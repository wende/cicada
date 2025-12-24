"""
Git history formatting utilities.

This module centralizes all formatting logic for git history, blame, and PR data.
"""

from typing import Any


class GitFormatter:
    """Centralized formatter for git history data."""

    @staticmethod
    def format_result(result: dict[str, Any], format_opts: dict[str, Any] | None = None) -> str:
        """
        Format analysis result as markdown.

        Args:
            result: Result from HistoryAnalyzer.analyze() method
            format_opts: Optional formatting options:
                - include_pr_description: Include PR descriptions (default: False)
                - include_review_comments: Include PR review comments (default: False)

        Returns:
            Formatted markdown string
        """
        result_type = result["type"]
        data = result["data"]
        opts = format_opts or {}

        if data is None:
            error = result.get("error", "No data available")
            return f"**Error:** {error}"

        formatter_map = {
            "single_line": GitFormatter._format_single_line,
            "line_range": GitFormatter._format_line_range,
            "function": GitFormatter._format_function,
        }

        if result_type == "file":
            return GitFormatter._format_file(data, result["pr_enriched"], opts)

        formatter = formatter_map.get(result_type)
        return formatter(data) if formatter else f"**Unknown result type:** {result_type}"

    @staticmethod
    def format_file_history(
        file_path: str,
        commits: list[dict[str, Any]],
        function_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        evolution: dict[str, Any] | None = None,
        tracking_method: str = "file",
        warning_msg: str = "",
        filter_info: str = "",
    ) -> str:
        """
        Format file history with commits.

        Args:
            file_path: Path to the file
            commits: List of commit dictionaries
            function_name: Optional function name being tracked
            start_line: Optional starting line
            end_line: Optional ending line
            evolution: Optional evolution metadata
            tracking_method: "file", "function", or "line"
            warning_msg: Optional warning message
            filter_info: Optional filter information

        Returns:
            Formatted markdown string
        """
        # Build title
        if function_name:
            title = f"Git History for {function_name} in {file_path}"
        elif start_line and end_line:
            title = f"Git History for {file_path} (lines {start_line}-{end_line})"
        else:
            title = f"Git History for {file_path}"

        lines = [f"# {title}\n"]

        # Add warning if present
        if warning_msg:
            lines.append(warning_msg)

        # Add filter information
        if filter_info:
            lines.append(f"*{filter_info}*\n")

        # Add tracking method info
        if tracking_method == "function":
            lines.append(
                "*Using function tracking (git log -L :funcname:file) - tracks function even as it moves*\n"
            )
        elif tracking_method == "line":
            lines.append("*Using line-based tracking (git log -L start,end:file)*\n")

        # Add evolution metadata if available
        if evolution:
            lines.append("## Function Evolution\n")
            created = evolution["created_at"]
            modified = evolution["last_modified"]

            lines.append(
                f"- **Created:** {created['date'][:10]} by {created['author']} (commit `{created['sha']}`)"
            )
            lines.append(
                f"- **Last Modified:** {modified['date'][:10]} by {modified['author']} (commit `{modified['sha']}`)"
            )
            lines.append(f"- **Total Modifications:** {evolution['total_modifications']} commit(s)")

            if evolution.get("modification_frequency"):
                freq = evolution["modification_frequency"]
                lines.append(f"- **Modification Frequency:** {freq:.2f} commits/month")

            lines.append("")  # Empty line

        lines.append(f"Found {len(commits)} commit(s)\n")

        for i, commit in enumerate(commits, 1):
            # Extract just the date (YYYY-MM-DD) from the full datetime string
            date_only = commit["date"][:10] if len(commit["date"]) >= 10 else commit["date"]

            lines.append(f"{i}. {commit['summary']}")
            lines.append(f"   {commit['sha']} • {commit['author']} • {date_only}")

            # Add relevance indicator for function searches
            if "relevance" in commit:
                relevance_text = (
                    "[Function mentioned]"
                    if commit["relevance"] == "mentioned"
                    else "[File changed]"
                )
                lines.append(f"   {relevance_text}")

            lines.append("")  # Empty line between commits

        return "\n".join(lines)

    @staticmethod
    def format_blame(
        file_path: str, start_line: int, end_line: int, blame_groups: list[dict[str, Any]]
    ) -> str:
        """
        Format blame information as markdown.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number
            blame_groups: List of blame group dictionaries

        Returns:
            Formatted markdown string
        """
        lines = [f"# Git Blame for {file_path} (lines {start_line}-{end_line})\n"]
        lines.append(f"Found {len(blame_groups)} authorship group(s)\n")

        for i, group in enumerate(blame_groups, 1):
            # Header with line range: ## 1/4 • Lines 37-38
            line_range = f"Lines {group['line_start']}-{group['line_end']}"
            lines.append(f"## {i}/{len(blame_groups)} • {line_range}")

            # Author line with indentation
            lines.append(f"  Author: {group['author']}")

            # Commit line with hash and date
            lines.append(f"  Commit: {group['sha']} • {group['date'][:10]}")

            # Empty line before code block
            lines.append("")

            # Show code lines with 3-space indentation
            lines.append("  ```")
            for line_info in group["lines"]:
                # Show line content with 5 spaces total (2 for block + 3 for content)
                lines.append(f"     {line_info['content']}")
            lines.append("  ```")

            # Empty line and separator
            lines.append("")
            lines.append("  ---\n")

        return "\n".join(lines)

    @staticmethod
    def _append_code_block(
        lines: list[str], code_lines: list[dict[str, Any]], allow_long: bool = False
    ) -> None:
        """
        Append a code block to lines list.

        Args:
            lines: List to append to
            code_lines: Code lines to format
            allow_long: If True, allow more lines and use truncation
        """
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

    @staticmethod
    def _format_single_line(data: dict[str, Any]) -> str:
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
            GitFormatter._append_code_block(lines, code_lines)

        return "\n".join(lines)

    @staticmethod
    def _format_line_range(data: dict[str, Any]) -> str:
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
                GitFormatter._append_code_block(lines, code_lines, allow_long=True)

            # Show PR if available
            pr = group.get("pr")
            if pr:
                pr_status = "merged" if pr.get("merged") else pr.get("status", "unknown")
                lines.append(
                    f"**PR:** [#{pr['number']}]({pr['url']}) - {pr['title']} (@{pr['author']}, {pr_status})"
                )

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_function(data: dict[str, Any]) -> str:
        """Format function history result."""
        lines = [
            f"## Function {data['function_name']} in {data['file_path']}",
            "",
        ]

        # Check if filters excluded all results
        filter_desc = data.get("filter_desc")
        total_before = data.get("total_before_filter", 0)
        if filter_desc and total_before:
            lines.append(
                f"**Found {total_before} commit(s) but none match filters:** {filter_desc}"
            )
            lines.append("")
            lines.append("*Try:*")
            lines.append("- Removing or adjusting the date filter")
            lines.append("- Using `recent=false` to see older commits")
            lines.append("- Omitting the `recent` parameter to see all commits")
            return "\n".join(lines)

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

    @staticmethod
    def _format_file(
        data: dict[str, Any], pr_enriched: bool, opts: dict[str, Any] | None = None
    ) -> str:
        """Format file history result.

        Args:
            data: File history data
            pr_enriched: Whether PR data was included
            opts: Formatting options:
                - include_pr_description: Include PR descriptions (default: False)
                - include_review_comments: Include PR review comments (default: False)
        """
        file_path = data["file_path"]
        lines = [f"## History for {file_path}", ""]
        opts = opts or {}
        include_desc = opts.get("include_pr_description", False)
        include_comments = opts.get("include_review_comments", False)

        if not pr_enriched:
            commits = data.get("commits", [])
            filter_desc = data.get("filter_desc")

            # Show helpful message if filters excluded all results
            if not commits and filter_desc:
                lines.append(f"No commits matching: {filter_desc}")
                return "\n".join(lines)

            # Show commits in compact format
            for commit in commits:
                lines.append(
                    f"- {commit['sha']} ({commit['date'][:10]}) @{commit['author']}: {commit['summary']}"
                )
            return "\n".join(lines)

        # PR-enriched results - compact by default
        prs = data.get("prs", [])
        if not prs:
            lines.append("No PRs found for this file")
            return "\n".join(lines)

        for pr in prs:
            date = pr.get("merged_at") or pr.get("created_at", "")
            date_str = date[:10] if date else ""

            # Compact: PR number, title, author, date on one line
            lines.append(f"- PR #{pr['number']} \"{pr['title']}\" @{pr['author']} {date_str}")

            # Include description if requested
            if include_desc:
                description = pr.get("description", "")
                if description:
                    desc_lines = description.split("\n")
                    for line in desc_lines[:10]:
                        lines.append(f"  {line}")
                    if len(desc_lines) > 10:
                        lines.append("  *(truncated)*")

            # Include comments if requested
            if include_comments:
                comments = pr.get("comments", [])
                if comments:
                    lines.append("  **Comments:**")
                    for comment in comments[:5]:
                        line_num = comment.get("line")
                        author = comment.get("author", "unknown")
                        body = comment.get("body", "")
                        resolved = " ✓" if comment.get("resolved") else ""
                        location = f"L{line_num}" if line_num is not None else "PR"
                        lines.append(f"  > {location} @{author}{resolved}: {body[:100]}")

        return "\n".join(lines)
