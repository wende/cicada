"""
PR Finder - Find the Pull Request that introduced a specific line of code.

Uses git blame to find the commit and GitHub API to find the associated PR.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from cicada.utils import is_git_repository, load_index


class PRFinder:
    """Find the PR that introduced a specific line of code."""

    def __init__(
        self,
        repo_path: str = ".",
        use_index: bool = True,
        index_path: str | None = None,
        verbose: bool = False,
    ):
        """
        Initialize the PR finder.

        Args:
            repo_path: Path to the git repository (defaults to current directory)
            use_index: If True, use cached index for PR lookups (default: True)
            index_path: Path to the PR index file (default: centralized storage)
            verbose: If True, print status messages (default: False)
        """
        from cicada.utils.storage import get_pr_index_path

        self.repo_path = Path(repo_path).resolve()
        self.use_index = use_index
        # Use centralized storage by default
        self.index_path = (
            index_path if index_path is not None else str(get_pr_index_path(self.repo_path))
        )
        self.index: dict[str, Any] | None = None
        self.verbose = verbose

        self._validate_git_repo()

        # Load index if enabled
        if self.use_index:
            self.index = self._load_index()
            if self.index and self.verbose:
                print(f"Loaded PR index with {self.index['metadata']['total_prs']} PRs")
            elif not self.index:
                # Always show warning (even in non-verbose mode) with color
                print(
                    "\033[33mWARNING: No PR index found - using slower network lookups. Create index: cicada index-pr\033[0m",
                    file=sys.stderr,
                )

        # Only validate gh CLI if we might need it (no index or index disabled)
        if not self.use_index or not self.index:
            self._validate_gh_cli()

    def _validate_git_repo(self):
        """Validate that the path is a git repository."""
        if not is_git_repository(self.repo_path):
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _validate_gh_cli(self):
        """Validate that GitHub CLI is installed and available."""
        try:
            _ = subprocess.run(
                ["gh", "--version"], capture_output=True, check=True, cwd=self.repo_path
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "GitHub CLI (gh) is not installed or not available in PATH. "
                "Install it from https://cli.github.com/"
            ) from None

    def _load_index(self) -> dict[str, Any] | None:
        """
        Load the PR index from file.

        Returns:
            Index dictionary or None if file doesn't exist or can't be loaded
        """
        # Try absolute path first
        index_file = Path(self.index_path)

        # If relative path, try relative to repo root
        if not index_file.is_absolute():
            index_file = self.repo_path / self.index_path

        return load_index(index_file, verbose=self.verbose, raise_on_error=False)

    def _lookup_pr_in_index(self, commit_sha: str) -> dict[str, Any] | None:
        """
        Look up PR information from the index.

        Args:
            commit_sha: Git commit SHA

        Returns:
            PR information dictionary or None if not found
        """
        if not self.index:
            return None

        # Look up commit in the commit_to_pr mapping
        pr_number = self.index.get("commit_to_pr", {}).get(commit_sha)

        if pr_number is None:
            return None

        # Get PR details
        pr = self.index.get("prs", {}).get(str(pr_number))

        return pr

    def _run_git_blame(self, file_path: str, line_number: int) -> dict[str, str | None] | None:
        """
        Run git blame to find the commit that introduced a specific line.

        Args:
            file_path: Relative path to the file from repo root
            line_number: Line number (1-indexed)

        Returns:
            Dictionary with commit SHA and author information, or None if not found
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "blame",
                    "-L",
                    f"{line_number},{line_number}",
                    "--porcelain",
                    file_path,
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            # Parse porcelain output
            lines = result.stdout.split("\n")
            commit_sha = lines[0].split()[0]

            # Extract author information from porcelain output
            author_name = None
            author_email = None

            for line in lines:
                if line.startswith("author "):
                    author_name = line[7:]  # Skip 'author '
                elif line.startswith("author-mail "):
                    author_email = line[12:].strip("<>")  # Skip 'author-mail ' and remove < >

            return {
                "commit": commit_sha,
                "author_name": author_name,
                "author_email": author_email,
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"git blame failed: {e.stderr}") from e

    def _get_repo_info(self) -> tuple[str, str] | None:
        """
        Get the repository owner and name from git remote.

        Returns:
            Tuple of (owner, repo_name), or None if not a GitHub repository
        """
        try:
            result = subprocess.run(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "-q",
                    ".nameWithOwner",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            name_with_owner = result.stdout.strip()
            if not name_with_owner or name_with_owner == "null":
                return None

            owner, repo_name = name_with_owner.split("/")
            return owner, repo_name

        except subprocess.CalledProcessError:
            # Not a GitHub repository or no remote configured
            return None

    def _find_pr_for_commit(self, commit_sha: str) -> dict[str, Any] | None:
        """
        Find the PR that introduced a specific commit.

        Args:
            commit_sha: Git commit SHA

        Returns:
            Dictionary containing PR information, or None if no PR found
        """
        try:
            repo_info = self._get_repo_info()
            if repo_info is None:
                # Not a GitHub repository
                return None

            owner, repo_name = repo_info

            # Query GitHub API for PRs associated with the commit
            result = subprocess.run(
                ["gh", "api", f"repos/{owner}/{repo_name}/commits/{commit_sha}/pulls"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )

            prs = json.loads(result.stdout)

            if not prs:
                return None

            # Return the first PR (usually there's only one)
            pr = prs[0]
            return {
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
                "state": pr["state"],
                "merged": pr.get("merged_at") is not None,
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "merged_at": pr.get("merged_at"),
            }

        except subprocess.CalledProcessError:
            # Commit might not be associated with a PR
            return None
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to parse PR information: {e}") from e

    def find_pr_for_line(self, file_path: str, line_number: int) -> dict[str, Any]:
        """
        Find the PR that introduced a specific line of code.

        Args:
            file_path: Path to the file (relative to repo root or absolute)
            line_number: Line number (1-indexed)

        Returns:
            Dictionary containing:
                - commit: The commit SHA
                - author_name: The commit author's name
                - author_email: The commit author's email
                - file_path: The file path
                - line_number: The line number
                - pr: PR information (or None if not found)
        """
        # Convert to relative path from repo root
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            file_path_obj = file_path_obj.relative_to(self.repo_path)

        file_path_str = str(file_path_obj)

        # Get commit and author info from git blame
        blame_info = self._run_git_blame(file_path_str, line_number)

        if not blame_info:
            return {
                "file_path": file_path_str,
                "line_number": line_number,
                "commit": None,
                "author_name": None,
                "author_email": None,
                "pr": None,
                "error": "Could not find commit for this line",
            }

        # Find PR for the commit - check index first, then network
        pr_info = None
        commit_sha = blame_info["commit"]
        assert commit_sha is not None

        if self.use_index and self.index:
            # Try index lookup first (fast, no network)
            pr_info = self._lookup_pr_in_index(commit_sha)

        # Fall back to network lookup if not found in index
        if pr_info is None and (not self.use_index or not self.index):
            pr_info = self._find_pr_for_commit(commit_sha)

        return {
            "file_path": file_path_str,
            "line_number": line_number,
            "commit": blame_info["commit"],
            "author_name": blame_info["author_name"],
            "author_email": blame_info["author_email"],
            "pr": pr_info,
        }

    def format_result(self, result: dict[str, Any], output_format: str = "text") -> str:
        """
        Format the result for display.

        Args:
            result: Result dictionary from find_pr_for_line
            output_format: Output format ('text', 'json', or 'markdown')

        Returns:
            Formatted string
        """
        if output_format == "json":
            return json.dumps(result, indent=2)

        if result.get("error"):
            return f"Error: {result['error']}"

        pr = result.get("pr")
        commit = result.get("commit")
        author_name = result.get("author_name")
        author_email = result.get("author_email")

        # Use short commit SHA for display (first 7 characters)
        short_commit = commit[:7] if commit and len(commit) >= 7 else commit

        # Format author string
        if author_name and author_email:
            author_str = f"{author_name} <{author_email}>"
        elif author_name:
            author_str = author_name
        elif author_email:
            author_str = author_email
        else:
            author_str = "Unknown"

        if output_format == "markdown":
            output = [
                f"## Line {result['line_number']} in {result['file_path']}",
                "",
                f"**Commit:** `{short_commit}`  ",
                f"**Author:** {author_str}",
            ]

            if pr:
                pr_status = "merged" if pr["merged"] else pr["state"]
                output.append(
                    f"**PR:** [#{pr['number']}]({pr['url']}) - {pr['title']} (@{pr['author']}, {pr_status})"
                )
            else:
                note = result.get("note", "None")
                output.append(f"**PR:** {note}")

            return "\n".join(output)

        else:  # text format
            output = [
                f"File: {result['file_path']}:{result['line_number']}",
                f"Commit: {short_commit}",
                f"Author: {author_str}",
            ]

            if pr:
                pr_status = "merged" if pr["merged"] else pr["state"]
                output.append(
                    f"PR: #{pr['number']} - {pr['title']} (@{pr['author']}, {pr_status}) - {pr['url']}"
                )
            else:
                note = result.get("note", "None")
                output.append(f"PR: {note}")

            return "\n".join(output)
