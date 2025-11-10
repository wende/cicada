"""
PR History Tool Handlers.

Handles tools related to pull request history and information.
"""

from pathlib import Path
from typing import Any

from mcp.types import TextContent

from cicada.github import PRFinder
from cicada.utils import get_pr_index_path


class PRHistoryHandler:
    """Handler for PR history-related tools."""

    def __init__(self, pr_index: dict[str, Any] | None, config: dict[str, Any]):
        """
        Initialize the PR history handler.

        Args:
            pr_index: The PR index containing PR data, or None if not loaded
            config: Configuration dictionary
        """
        self.pr_index = pr_index
        self.config = config

    def get_recent_pr_info(self, file_path: str) -> dict | None:
        """
        Get the most recent PR that modified a file.

        Args:
            file_path: Relative path to the file

        Returns:
            Dictionary with PR info (number, title, date, comment_count) or None
        """
        if not self.pr_index:
            return None

        # Look up PRs for this file
        file_to_prs = self.pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path, [])

        if not pr_numbers:
            return None

        # Get the most recent PR (last in list)
        prs_data = self.pr_index.get("prs", {})
        most_recent_pr_num = pr_numbers[-1]
        pr = prs_data.get(str(most_recent_pr_num))

        if not pr:
            return None

        # Count comments for this file
        comments = pr.get("comments", [])
        file_comments = [c for c in comments if c.get("path") == file_path]

        return {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr.get("author", "unknown"),
            "comment_count": len(file_comments),
            "url": pr.get("url", ""),
        }

    async def find_pr_for_line(
        self, file_path: str, line_number: int, output_format: str = "text"
    ) -> list[TextContent]:
        """
        Find the PR that introduced a specific line of code.

        Args:
            file_path: Path to the file
            line_number: Line number (1-indexed)
            output_format: Output format ('text', 'json', or 'markdown')

        Returns:
            TextContent with PR information
        """
        try:
            # Get repo path from config
            repo_path = self.config.get("repository", {}).get("path", ".")
            index_path = get_pr_index_path(repo_path)

            # Check if index exists
            if not index_path.exists():
                error_msg = (
                    "PR index not found. Please run:\n"
                    "  cicada index-pr\n\n"
                    f"This will create the PR index at {index_path}"
                )
                return [TextContent(type="text", text=error_msg)]

            # Initialize PRFinder with index enabled
            pr_finder = PRFinder(
                repo_path=repo_path,
                use_index=True,
                index_path=str(index_path),
                verbose=False,
            )

            # Find PR for the line using index
            result = pr_finder.find_pr_for_line(file_path, line_number)

            # If no PR found in index, check if it exists via network
            if result.get("pr") is None and result.get("commit"):
                # Try network lookup to see if PR actually exists
                pr_finder_network = PRFinder(
                    repo_path=repo_path,
                    use_index=False,
                    verbose=False,
                )
                network_result = pr_finder_network.find_pr_for_line(file_path, line_number)

                if network_result.get("pr") is not None:
                    # PR exists but not in index - suggest update
                    error_msg = (
                        "PR index is incomplete. Please run:\n"
                        "  cicada index-pr\n\n"
                        "This will update the index with recent PRs (incremental by default)."
                    )
                    return [TextContent(type="text", text=error_msg)]
                else:
                    # No PR associated with this commit
                    result["pr"] = None  # Ensure it's explicitly None
                    result["note"] = "No PR associated with this line"

            # Format the result
            formatted_result = pr_finder.format_result(result, output_format)

            return [TextContent(type="text", text=formatted_result)]

        except Exception as e:
            error_msg = f"Error finding PR: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def get_file_pr_history(self, file_path: str) -> list[TextContent]:
        """
        Get all PRs that modified a specific file with descriptions and comments.

        Args:
            file_path: Path to the file (relative to repo root or absolute)

        Returns:
            TextContent with formatted PR history
        """
        if not self.pr_index:
            error_msg = (
                "PR index not available. Please run:\n"
                "  cicada index-pr\n\n"
                "This will create the PR index at .cicada/pr_index.json"
            )
            return [TextContent(type="text", text=error_msg)]

        # Normalize file path
        repo_path = Path(self.config.get("repository", {}).get("path", "."))
        file_path_obj = Path(file_path)

        if file_path_obj.is_absolute():
            try:
                file_path_obj = file_path_obj.relative_to(repo_path)
            except ValueError:
                error_msg = f"File path {file_path} is not within repository {repo_path}"
                return [TextContent(type="text", text=error_msg)]

        file_path_str = str(file_path_obj)

        # Look up PRs that touched this file
        file_to_prs = self.pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path_str, [])

        if not pr_numbers:
            result = f"No pull requests found that modified: {file_path_str}"
            return [TextContent(type="text", text=result)]

        # Get PR details
        prs_data = self.pr_index.get("prs", {})

        # Format results as markdown
        lines = [f"# Pull Request History for {file_path_str}\n"]
        lines.append(f"Found {len(pr_numbers)} pull request(s)\n")

        for pr_num in pr_numbers:
            pr = prs_data.get(str(pr_num))
            if not pr:
                continue

            # PR Header
            status = "merged" if pr.get("merged") else pr.get("state", "unknown")
            lines.append(f"## PR #{pr['number']}: {pr['title']}")
            lines.append(f"- **Author:** @{pr['author']}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **URL:** {pr['url']}\n")

            # PR Description (trimmed to first 10 lines)
            description = pr.get("description", "").strip()
            if description:
                lines.append("### Description")
                desc_lines = description.split("\n")
                if len(desc_lines) > 10:
                    trimmed_desc = "\n".join(desc_lines[:10])
                    lines.append(f"{trimmed_desc}")
                    lines.append(f"\n*... (trimmed, {len(desc_lines) - 10} more lines)*\n")
                else:
                    lines.append(f"{description}\n")

            # Review Comments for this file only
            comments = pr.get("comments", [])
            file_comments = [c for c in comments if c.get("path") == file_path_str]

            if file_comments:
                lines.append(f"### Review Comments ({len(file_comments)})")

                for comment in file_comments:
                    author = comment.get("author", "unknown")
                    body = comment.get("body", "").strip()
                    line_num = comment.get("line")
                    original_line = comment.get("original_line")
                    resolved = comment.get("resolved", False)

                    # Comment header with line info
                    if line_num:
                        line_info = f"Line {line_num}"
                    elif original_line:
                        line_info = f"Original line {original_line} (unmapped)"
                    else:
                        line_info = "No line info"

                    resolved_marker = " ✓ Resolved" if resolved else ""
                    lines.append(f"\n**@{author}** ({line_info}){resolved_marker}:")

                    # Indent comment body
                    for line in body.split("\n"):
                        lines.append(f"> {line}")

                lines.append("")  # Empty line after comments

            lines.append("---\n")  # Separator between PRs

        result = "\n".join(lines)
        return [TextContent(type="text", text=result)]
