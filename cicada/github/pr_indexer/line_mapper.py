"""
Line Mapper for PR Comments.

This module handles mapping comment line numbers from PR commits to current HEAD,
allowing comments to track code changes over time.
"""

import subprocess
from pathlib import Path
from typing import Any

from cicada.utils import SubprocessRunner


class LineMapper:
    """
    Maps comment line numbers from PR commits to current file state.

    When a PR comment is made on a specific line, that line might move
    or be deleted as the codebase evolves. This class attempts to track
    those changes.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize the line mapper.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self.runner = SubprocessRunner(cwd=repo_path)

    def map_all_comment_lines(self, prs: list[dict[str, Any]]) -> None:
        """
        Map all comment lines in PRs to current line numbers.

        This updates the PRs in-place, setting the 'line' field for each comment.

        Args:
            prs: List of PR dictionaries to update in-place
        """
        print("Mapping comment lines to current file state...")

        total_comments = sum(len(pr.get("comments", [])) for pr in prs)
        if total_comments == 0:
            return

        mapped_count = 0
        unmapped_count = 0

        try:
            for pr in prs:
                for comment in pr.get("comments", []):
                    original_line = comment.get("original_line")
                    commit_sha = comment.get("commit_sha")
                    file_path = comment.get("path")

                    if original_line and commit_sha and file_path:
                        current_line = self.map_line_to_current(
                            file_path, original_line, commit_sha
                        )
                        comment["line"] = current_line

                        if current_line is not None:
                            mapped_count += 1
                        else:
                            unmapped_count += 1
                    else:
                        comment["line"] = None
                        unmapped_count += 1

        except KeyboardInterrupt:
            print(
                f"\n\nWARNING: Line mapping interrupted. "
                f"Mapped {mapped_count}/{total_comments} comments."
            )
            print("Saving index with partial line mappings...")
            # Re-raise to let the outer handler save the index
            raise

        print(f"  Mapped {mapped_count} comments, {unmapped_count} unmappable/outdated")

    def map_line_to_current(
        self, file_path: str, original_line: int, commit_sha: str
    ) -> int | None:
        """
        Map a line number from a PR commit to the current HEAD.

        This is a best-effort attempt that:
        1. Checks if the file still exists
        2. Tries to find the same line content in the current file
        3. Searches within a reasonable range if exact position doesn't match

        Args:
            file_path: Path to the file
            original_line: Line number in the PR commit
            commit_sha: The commit SHA where the comment was made

        Returns:
            Current line number, or None if line no longer exists or can't be tracked
        """
        if not original_line or not commit_sha or not file_path:
            return None

        try:
            # Check if the file still exists
            if not self._file_exists(file_path):
                return None

            # Get current file lines
            current_lines = self._get_file_lines("HEAD", file_path)
            if not current_lines:
                return None

            # Get original file lines
            original_lines = self._get_file_lines(commit_sha, file_path)
            if not original_lines or original_line > len(original_lines):
                return None

            # Get the actual line content from the original commit
            original_content = original_lines[original_line - 1].strip()

            if not original_content:
                # Empty line, can't track reliably
                return None

            # Search for the same content in current file
            # Look for exact match near the original line number
            current_line = self._find_matching_line(current_lines, original_content, original_line)

            return current_line

        except (subprocess.CalledProcessError, IndexError, ValueError):
            return None

    def _file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in the current HEAD.

        Args:
            file_path: Path to the file

        Returns:
            True if file exists
        """
        try:
            result = self.runner.run_git_command(["ls-files", file_path], check=False)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def _get_file_lines(self, ref: str, file_path: str) -> list[str] | None:
        """
        Get file lines at a specific git ref.

        Args:
            ref: Git reference (commit SHA, branch name, HEAD, etc.)
            file_path: Path to the file

        Returns:
            List of file lines, or None if file doesn't exist at that ref
        """
        try:
            result = self.runner.run_git_command(["show", f"{ref}:{file_path}"], check=False)

            if result.returncode != 0:
                return None

            return result.stdout.split("\n")

        except subprocess.CalledProcessError:
            return None

    def _find_matching_line(
        self,
        current_lines: list[str],
        original_content: str,
        original_line: int,
        search_range: int = 20,
    ) -> int | None:
        """
        Find a matching line in the current file.

        Searches for an exact content match near the original line number.

        Args:
            current_lines: Lines from the current file
            original_content: Original line content (stripped)
            original_line: Original line number
            search_range: How many lines to search above/below (default: 20)

        Returns:
            Matching line number (1-indexed), or None if not found
        """
        # Search within a range near the original line
        start = max(1, original_line - search_range)
        end = min(len(current_lines), original_line + search_range)

        for i in range(start - 1, end):
            if current_lines[i].strip() == original_content:
                return i + 1

        # If not found nearby, return None (line likely deleted/changed)
        return None
