"""
Author: Cursor(Auto)

GitHub API Client for PR Indexer.

This module handles all interactions with the GitHub API (both REST and GraphQL),
separating API concerns from indexing logic.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from cicada.utils import SubprocessRunner


class GitHubAPIClient:
    """
    Handles GitHub API interactions for PR indexing.

    This class encapsulates all GitHub CLI and API calls, providing
    a clean interface for fetching PR data.
    """

    def __init__(self, repo_path: Path, repo_owner: str, repo_name: str):
        """
        Initialize the GitHub API client.

        Args:
            repo_path: Path to the git repository
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
        """
        self.repo_path = repo_path
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.runner = SubprocessRunner(cwd=repo_path)

    def validate_gh_cli(self) -> None:
        """
        Validate that GitHub CLI is installed and available.

        Raises:
            RuntimeError: If gh CLI is not available
        """
        try:
            self.runner.run_gh_command("--version")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "GitHub CLI (gh) is not installed or not available in PATH. "
                "Install it from https://cli.github.com/"
            ) from None

    def get_repo_info(self) -> tuple[str, str]:
        """
        Get repository owner and name from git remote.

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            RuntimeError: If not a GitHub repository
        """
        try:
            result = self.runner.run_gh_command(
                ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
            )

            name_with_owner = result.stdout.strip()
            if not name_with_owner or name_with_owner == "null":
                raise RuntimeError("Not a GitHub repository or no remote configured")

            parts = name_with_owner.split("/")
            if len(parts) != 2:
                raise RuntimeError(
                    f"Invalid repository format. Expected owner/repo, got: {name_with_owner}"
                )

            owner, repo_name = parts
            return owner, repo_name

        except subprocess.CalledProcessError:
            raise RuntimeError("Not a GitHub repository or no remote configured") from None

    def fetch_pr_list(self, state: str = "all", limit: int = 10000) -> list[int]:
        """
        Fetch list of PR numbers.

        Args:
            state: PR state filter ('all', 'open', 'closed', 'merged')
            limit: Maximum number of PRs to fetch

        Returns:
            List of PR numbers

        Raises:
            RuntimeError: If fetching fails
        """
        try:
            result = self.runner.run_gh_command(
                [
                    "pr",
                    "list",
                    "--state",
                    state,
                    "--json",
                    "number",
                    "--limit",
                    str(limit),
                ]
            )

            pr_list = json.loads(result.stdout)
            return [pr["number"] for pr in pr_list]

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR list: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR list: {e}") from e

    def fetch_prs_batch_graphql(self, pr_numbers: list[int]) -> list[dict[str, Any]]:
        """
        Fetch detailed PR information for a batch using GraphQL.

        This is much more efficient than making individual REST calls.

        Args:
            pr_numbers: List of PR numbers to fetch (max 10 recommended)

        Returns:
            List of detailed PR dictionaries

        Raises:
            RuntimeError: If GraphQL query fails
        """
        if not pr_numbers:
            return []

        # Build GraphQL query for batch fetching
        pr_queries: list[str] = []
        for i, num in enumerate(pr_numbers):
            pr_queries.append(
                f"""
                pr{i}: pullRequest(number: {num}) {{
                    number
                    title
                    url
                    state
                    mergedAt
                    bodyText
                    author {{ login }}
                    commits(first: 250) {{
                        nodes {{ commit {{ oid }} }}
                    }}
                    files(first: 100) {{
                        nodes {{ path }}
                    }}
                    reviewThreads(first: 100) {{
                        nodes {{
                            isResolved
                            comments(first: 10) {{
                                nodes {{
                                    id
                                    body
                                    createdAt
                                    author {{ login }}
                                    path
                                    position
                                    originalPosition
                                    line
                                    originalLine
                                    diffHunk
                                    commit {{ oid }}
                                }}
                            }}
                        }}
                    }}
                }}
            """
            )

        query = f"""
            query {{
                repository(owner: "{self.repo_owner}", name: "{self.repo_name}") {{
                    {' '.join(pr_queries)}
                }}
            }}
        """

        try:
            result = self.runner.run_gh_command(["api", "graphql", "-f", f"query={query}"])

            data = json.loads(result.stdout)
            repo_data = data.get("data", {}).get("repository", {})

            return self._parse_graphql_response(repo_data, len(pr_numbers))

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"GraphQL query failed for PRs {pr_numbers}: {e.stderr}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to parse GraphQL response for PRs {pr_numbers}: {e}") from e

    def _parse_graphql_response(
        self, repo_data: dict[str, Any], num_prs: int
    ) -> list[dict[str, Any]]:
        """
        Parse GraphQL response into PR dictionaries.

        Args:
            repo_data: Repository data from GraphQL response
            num_prs: Number of PRs in the batch

        Returns:
            List of parsed PR dictionaries
        """
        detailed_prs = []

        for i in range(num_prs):
            pr_data = repo_data.get(f"pr{i}")
            if not pr_data:
                continue

            # Extract commits
            commits = [
                node["commit"]["oid"] for node in pr_data.get("commits", {}).get("nodes", [])
            ]

            # Extract files
            files = [node["path"] for node in pr_data.get("files", {}).get("nodes", [])]

            # Extract and flatten review thread comments
            comments = self._parse_review_comments(pr_data)

            detailed_pr = {
                "number": pr_data["number"],
                "title": pr_data["title"],
                "url": pr_data["url"],
                "state": pr_data["state"].lower(),
                "merged": pr_data.get("mergedAt") is not None,
                "merged_at": pr_data.get("mergedAt"),
                "author": (pr_data.get("author") or {}).get("login", "unknown"),
                "description": pr_data.get("bodyText", ""),
                "commits": commits,
                "files_changed": files,
                "comments": comments,
            }

            detailed_prs.append(detailed_pr)

        return detailed_prs

    def _parse_review_comments(self, pr_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse review thread comments from PR data.

        Args:
            pr_data: PR data from GraphQL

        Returns:
            List of comment dictionaries
        """
        comments = []

        for thread in pr_data.get("reviewThreads", {}).get("nodes", []):
            is_resolved = thread.get("isResolved", False)

            for comment_node in thread.get("comments", {}).get("nodes", []):
                # Map comment line to current file line (will be updated later)
                mapped_line = comment_node.get("line")

                comments.append(
                    {
                        "id": comment_node.get("id"),
                        "author": (comment_node.get("author") or {}).get("login", "unknown"),
                        "body": comment_node.get("body", ""),
                        "created_at": comment_node.get("createdAt"),
                        "path": comment_node.get("path"),
                        "line": mapped_line,  # Current line (to be mapped)
                        "original_line": comment_node.get("originalLine"),
                        "diff_hunk": comment_node.get("diffHunk"),
                        "resolved": is_resolved,
                        "commit_sha": (comment_node.get("commit") or {}).get("oid"),
                    }
                )

        return comments

    def fetch_pr_rest(self, pr_number: int) -> dict[str, Any]:
        """
        Fallback method to fetch a single PR using REST API.

        Args:
            pr_number: PR number to fetch

        Returns:
            PR dictionary

        Note:
            This is slower than GraphQL and doesn't include comments.
            Only used as a fallback if GraphQL fails.
        """
        commits = self._fetch_pr_commits_rest(pr_number)
        files = self._fetch_pr_files_rest(pr_number)

        try:
            result = self.runner.run_gh_command(
                [
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "number,title,url,state,mergedAt,author,body",
                ]
            )
            pr_data = json.loads(result.stdout)

            return {
                "number": pr_number,
                "title": pr_data.get("title", ""),
                "url": pr_data.get("url", ""),
                "state": pr_data.get("state", "").lower(),
                "merged": pr_data.get("mergedAt") is not None,
                "merged_at": pr_data.get("mergedAt"),
                "author": (pr_data.get("author") or {}).get("login", "unknown"),
                "description": pr_data.get("body", ""),
                "commits": commits,
                "files_changed": files,
                "comments": [],  # REST fallback doesn't fetch comments
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            # Return minimal PR info if everything fails
            return {
                "number": pr_number,
                "title": f"PR #{pr_number}",
                "url": f"https://github.com/{self.repo_owner}/{self.repo_name}/pull/{pr_number}",
                "state": "unknown",
                "merged": False,
                "merged_at": None,
                "author": "unknown",
                "description": "",
                "commits": commits,
                "files_changed": files,
                "comments": [],
            }

    def _fetch_pr_commits_rest(self, pr_number: int) -> list[str]:
        """
        Fetch commit SHAs for a PR using REST API.

        Args:
            pr_number: PR number

        Returns:
            List of commit SHAs
        """
        try:
            result = self.runner.run_gh_command(
                [
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "commits",
                    "-q",
                    ".commits[].oid",
                ]
            )

            commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            return commits

        except subprocess.CalledProcessError:
            return []

    def _fetch_pr_files_rest(self, pr_number: int) -> list[str]:
        """
        Fetch changed files for a PR using REST API.

        Args:
            pr_number: PR number

        Returns:
            List of file paths
        """
        try:
            result = self.runner.run_gh_command(
                ["pr", "view", str(pr_number), "--json", "files", "-q", ".files[].path"]
            )

            files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            return files

        except subprocess.CalledProcessError:
            return []

    def get_total_pr_count(self) -> int:
        """
        Get the actual total number of PRs in the repository.

        Uses GraphQL to get the exact count, avoiding issues with shared PR/issue
        numbering where the highest number doesn't equal the PR count.

        Returns:
            Actual count of pull requests
        """
        try:
            # Use GraphQL to get exact PR count
            query = """
            query($owner:String!, $repo:String!) {
                repository(owner: $owner, name: $repo) {
                    pullRequests(first: 0, states: [OPEN, CLOSED, MERGED]) {
                        totalCount
                    }
                }
            }
            """

            result = self.runner.run_gh_command(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"owner={self.repo_owner}",
                    "-f",
                    f"repo={self.repo_name}",
                    "-f",
                    f"query={query}",
                ]
            )

            data = json.loads(result.stdout)
            total_count = (
                data.get("data", {})
                .get("repository", {})
                .get("pullRequests", {})
                .get("totalCount", 0)
            )
            return total_count
        except (
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
        ):
            return 0
