"""
PR History Tool Handlers.

Handles tools related to pull request history and information.
"""

from typing import Any


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
