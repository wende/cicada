"""
Author: Cursor(Auto)

Comprehensive tests for GitHubAPIClient.

Tests all methods and error paths with proper mocking to achieve high coverage
while maintaining loose coupling to implementation details.
"""

from pathlib import Path

import pytest

from cicada.pr_indexer.github_api_client import GitHubAPIClient
from tests.mocks.github_responses import (
    create_empty_response,
    create_graphql_response,
    create_malformed_json_response,
    create_pr_list_response,
    create_pr_with_complex_comments,
    create_pr_with_no_metadata,
    create_rest_pr_response,
    create_single_pr_data,
)
from tests.mocks.subprocess_mocks import MockCompletedProcess, MockSubprocessRunner


class TestGitHubAPIClientInit:
    """Test GitHubAPIClient initialization and setup."""

    def test_init_with_valid_parameters(self, tmp_path):
        """Test initialization with valid parameters."""
        client = GitHubAPIClient(repo_path=tmp_path, repo_owner="testowner", repo_name="testrepo")

        assert client.repo_path == tmp_path
        assert client.repo_owner == "testowner"
        assert client.repo_name == "testrepo"
        assert client.runner is not None

    def test_init_with_path_object(self, tmp_path):
        """Test initialization with Path object."""
        client = GitHubAPIClient(
            repo_path=Path(tmp_path), repo_owner="testowner", repo_name="testrepo"
        )

        assert client.repo_path == tmp_path
        assert client.repo_owner == "testowner"
        assert client.repo_name == "testrepo"


class TestValidateGHCLI:
    """Test GitHub CLI validation."""

    def test_validate_gh_cli_success(self, tmp_path):
        """Test successful CLI validation."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="--version",
            response=MockCompletedProcess(returncode=0, stdout="gh version 2.0.0"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        # Should not raise exception
        client.validate_gh_cli()

        assert mock_runner.verify_called_with("gh --version")

    def test_validate_gh_cli_not_installed(self, tmp_path):
        """Test CLI validation when gh is not installed."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="--version",
            response=MockCompletedProcess(returncode=1, stderr="command not found"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="GitHub CLI \\(gh\\) is not installed"):
            client.validate_gh_cli()

    def test_validate_gh_cli_subprocess_error(self, tmp_path):
        """Test CLI validation with subprocess error."""
        # mock_runner = MockSubprocessRunner()  # Unused

        # No response configured, will use default (success)
        # But we can simulate FileNotFoundError by raising it
        def mock_run(*_args, **_kwargs):
            raise FileNotFoundError("gh: command not found")

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = MockSubprocessRunner()
        client.runner.run = mock_run

        with pytest.raises(RuntimeError, match="GitHub CLI \\(gh\\) is not installed"):
            client.validate_gh_cli()


class TestGetRepoInfo:
    """Test repository information retrieval."""

    def test_get_repo_info_success(self, tmp_path):
        """Test successful repo info retrieval."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh repo view --json nameWithOwner -q .nameWithOwner",
            response=MockCompletedProcess(returncode=0, stdout="testowner/testrepo"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        owner, repo_name = client.get_repo_info()

        assert owner == "testowner"
        assert repo_name == "testrepo"
        assert mock_runner.verify_called_with("gh repo view --json nameWithOwner -q .nameWithOwner")

    def test_get_repo_info_invalid_format(self, tmp_path):
        """Test repo info with invalid format."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh repo view --json nameWithOwner -q .nameWithOwner",
            response=MockCompletedProcess(returncode=0, stdout="invalid-format"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(
            RuntimeError,
            match="Invalid repository format. Expected owner/repo, got: invalid-format",
        ):
            _ = client.get_repo_info()

    def test_get_repo_info_null_response(self, tmp_path):
        """Test repo info with null response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh repo view --json nameWithOwner -q .nameWithOwner",
            response=MockCompletedProcess(returncode=0, stdout="null"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="Not a GitHub repository"):
            _ = client.get_repo_info()

    def test_get_repo_info_subprocess_error(self, tmp_path):
        """Test repo info with subprocess error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh repo view --json nameWithOwner -q .nameWithOwner",
            response=MockCompletedProcess(returncode=1, stderr="not a git repository"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="Not a GitHub repository"):
            _ = client.get_repo_info()


class TestFetchPRList:
    """Test PR list fetching."""

    def test_fetch_pr_list_success_all_state(self, tmp_path):
        """Test successful PR list fetching with all state."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 10000",
            response=MockCompletedProcess(returncode=0, stdout=create_pr_list_response(count=3)),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        prs = client.fetch_pr_list()

        assert prs == [1, 2, 3]
        assert mock_runner.verify_called_with("gh pr list --state all --json number --limit 10000")

    def test_fetch_pr_list_success_merged_state(self, tmp_path):
        """Test PR list fetching with merged state filter."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state merged --json number --limit 10000",
            response=MockCompletedProcess(
                returncode=0, stdout=create_pr_list_response(count=2, start_number=5)
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        prs = client.fetch_pr_list(state="merged")

        assert prs == [5, 6]
        assert mock_runner.verify_called_with(
            "gh pr list --state merged --json number --limit 10000"
        )

    def test_fetch_pr_list_with_limit(self, tmp_path):
        """Test PR list fetching with custom limit."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 5",
            response=MockCompletedProcess(returncode=0, stdout=create_pr_list_response(count=5)),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        prs = client.fetch_pr_list(limit=5)

        assert prs == [1, 2, 3, 4, 5]
        assert mock_runner.verify_called_with("gh pr list --state all --json number --limit 5")

    def test_fetch_pr_list_empty_response(self, tmp_path):
        """Test PR list fetching with empty response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 10000",
            response=MockCompletedProcess(returncode=0, stdout=create_empty_response()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        prs = client.fetch_pr_list()

        assert prs == []

    def test_fetch_pr_list_json_decode_error(self, tmp_path):
        """Test PR list fetching with JSON decode error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 10000",
            response=MockCompletedProcess(returncode=0, stdout=create_malformed_json_response()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="Failed to parse PR list"):
            _ = client.fetch_pr_list()

    def test_fetch_pr_list_subprocess_error(self, tmp_path):
        """Test PR list fetching with subprocess error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 10000",
            response=MockCompletedProcess(returncode=1, stderr="API rate limit exceeded"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="Failed to fetch PR list"):
            _ = client.fetch_pr_list()


class TestFetchPRsBatchGraphQL:
    """Test GraphQL batch fetching."""

    def test_fetch_prs_batch_empty_list(self, tmp_path):
        """Test batch fetching with empty PR list."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = MockSubprocessRunner()

        result = client.fetch_prs_batch_graphql([])

        assert result == []

    def test_fetch_prs_batch_single_pr(self, tmp_path):
        """Test batch fetching with single PR."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_graphql_response([create_single_pr_data(number=1)]),
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_prs_batch_graphql([1])

        assert len(result) == 1
        assert result[0]["number"] == 1
        assert result[0]["title"] == "Test PR"

    def test_fetch_prs_batch_multiple_prs(self, tmp_path):
        """Test batch fetching with multiple PRs."""
        mock_runner = MockSubprocessRunner()
        prs_data = [
            create_single_pr_data(number=1, title="PR 1"),
            create_single_pr_data(number=2, title="PR 2"),
            create_single_pr_data(number=3, title="PR 3"),
        ]
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(returncode=0, stdout=create_graphql_response(prs_data)),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_prs_batch_graphql([1, 2, 3])

        assert len(result) == 3
        assert result[0]["number"] == 1
        assert result[1]["number"] == 2
        assert result[2]["number"] == 3

    def test_fetch_prs_batch_with_comments(self, tmp_path):
        """Test batch fetching with review comments."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(returncode=0, stdout=create_pr_with_complex_comments()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_prs_batch_graphql([1])

        assert len(result) == 1
        assert len(result[0]["comments"]) > 0

    def test_fetch_prs_batch_with_files(self, tmp_path):
        """Test batch fetching with changed files."""
        mock_runner = MockSubprocessRunner()
        pr_data = create_single_pr_data(file_count=5)
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(returncode=0, stdout=create_graphql_response([pr_data])),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_prs_batch_graphql([1])

        assert len(result) == 1
        assert len(result[0]["files_changed"]) == 5

    def test_fetch_prs_batch_graphql_error(self, tmp_path):
        """Test batch fetching with GraphQL error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(
                returncode=1, stderr="GraphQL error: rate limit exceeded"
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="GraphQL query failed"):
            _ = client.fetch_prs_batch_graphql([1])

    def test_fetch_prs_batch_json_decode_error(self, tmp_path):
        """Test batch fetching with JSON decode error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(returncode=0, stdout=create_malformed_json_response()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        with pytest.raises(RuntimeError, match="Failed to parse GraphQL response"):
            _ = client.fetch_prs_batch_graphql([1])

    def test_fetch_prs_batch_missing_data(self, tmp_path):
        """Test batch fetching with missing data in response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh api graphql -f",
            response=MockCompletedProcess(returncode=0, stdout=create_pr_with_no_metadata()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_prs_batch_graphql([1])

        assert len(result) == 1
        assert result[0]["number"] == 1


class TestParseGraphQLResponse:
    """Test GraphQL response parsing."""

    def test_parse_graphql_response_complete(self, tmp_path):
        """Test parsing complete GraphQL response."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        repo_data = {
            "pr0": {
                "number": 1,
                "title": "Test PR",
                "url": "https://github.com/owner/repo/pull/1",
                "state": "MERGED",
                "mergedAt": "2023-01-01T00:00:00Z",
                "bodyText": "Test description",
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {"commit": {"oid": "abc123"}},
                        {"commit": {"oid": "def456"}},
                    ]
                },
                "files": {"nodes": [{"path": "file1.py"}, {"path": "file2.py"}]},
                "reviewThreads": {
                    "nodes": [
                        {
                            "isResolved": False,
                            "comments": {
                                "nodes": [
                                    {
                                        "id": "comment1",
                                        "body": "Test comment",
                                        "createdAt": "2023-01-01T00:00:00Z",
                                        "author": {"login": "reviewer"},
                                        "path": "file1.py",
                                        "line": 10,
                                        "originalLine": 10,
                                        "diffHunk": "@@ -10,0 +10,1 @@\n+comment",
                                        "commit": {"oid": "abc123"},
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        }

        result = client._parse_graphql_response(repo_data, 1)

        assert len(result) == 1
        pr = result[0]
        assert pr["number"] == 1
        assert pr["title"] == "Test PR"
        assert pr["state"] == "merged"
        assert pr["merged"] is True
        assert pr["author"] == "testuser"
        assert len(pr["commits"]) == 2
        assert len(pr["files_changed"]) == 2
        assert len(pr["comments"]) == 1

    def test_parse_graphql_response_missing_fields(self, tmp_path):
        """Test parsing response with missing fields."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        repo_data = {
            "pr0": {
                "number": 1,
                "title": "Test PR",
                "url": "https://github.com/owner/repo/pull/1",
                "state": "OPEN",
                "mergedAt": None,
                "bodyText": "",
                "author": None,
                "commits": {"nodes": []},
                "files": {"nodes": []},
                "reviewThreads": {"nodes": []},
            }
        }

        result = client._parse_graphql_response(repo_data, 1)

        assert len(result) == 1
        pr = result[0]
        assert pr["number"] == 1
        assert pr["state"] == "open"
        assert pr["merged"] is False
        assert pr["author"] == "unknown"
        assert pr["commits"] == []
        assert pr["files_changed"] == []
        assert pr["comments"] == []

    def test_parse_graphql_response_empty_commits(self, tmp_path):
        """Test parsing response with empty commits."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        repo_data = {
            "pr0": {
                "number": 1,
                "title": "Test PR",
                "url": "https://github.com/owner/repo/pull/1",
                "state": "OPEN",
                "mergedAt": None,
                "bodyText": "Test",
                "author": {"login": "user"},
                "commits": {"nodes": []},
                "files": {"nodes": [{"path": "file.py"}]},
                "reviewThreads": {"nodes": []},
            }
        }

        result = client._parse_graphql_response(repo_data, 1)

        assert len(result) == 1
        pr = result[0]
        assert pr["commits"] == []
        assert pr["files_changed"] == ["file.py"]

    def test_parse_graphql_response_empty_files(self, tmp_path):
        """Test parsing response with empty files."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        repo_data = {
            "pr0": {
                "number": 1,
                "title": "Test PR",
                "url": "https://github.com/owner/repo/pull/1",
                "state": "OPEN",
                "mergedAt": None,
                "bodyText": "Test",
                "author": {"login": "user"},
                "commits": {"nodes": [{"commit": {"oid": "abc123"}}]},
                "files": {"nodes": []},
                "reviewThreads": {"nodes": []},
            }
        }

        result = client._parse_graphql_response(repo_data, 1)

        assert len(result) == 1
        pr = result[0]
        assert pr["commits"] == ["abc123"]
        assert pr["files_changed"] == []


class TestParseReviewComments:
    """Test review comment parsing."""

    def test_parse_review_comments_with_threads(self, tmp_path):
        """Test parsing review comments with multiple threads."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        pr_data = {
            "reviewThreads": {
                "nodes": [
                    {
                        "isResolved": False,
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment1",
                                    "body": "Comment 1",
                                    "createdAt": "2023-01-01T00:00:00Z",
                                    "author": {"login": "user1"},
                                    "path": "file1.py",
                                    "line": 10,
                                    "originalLine": 10,
                                    "diffHunk": "@@ -10,0 +10,1 @@\n+comment",
                                    "commit": {"oid": "abc123"},
                                }
                            ]
                        },
                    },
                    {
                        "isResolved": True,
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment2",
                                    "body": "Comment 2",
                                    "createdAt": "2023-01-01T01:00:00Z",
                                    "author": {"login": "user2"},
                                    "path": "file2.py",
                                    "line": 20,
                                    "originalLine": 20,
                                    "diffHunk": "@@ -20,0 +20,1 @@\n+comment",
                                    "commit": {"oid": "def456"},
                                }
                            ]
                        },
                    },
                ]
            }
        }

        result = client._parse_review_comments(pr_data)

        assert len(result) == 2
        assert result[0]["id"] == "comment1"
        assert result[0]["resolved"] is False
        assert result[1]["id"] == "comment2"
        assert result[1]["resolved"] is True

    def test_parse_review_comments_resolved(self, tmp_path):
        """Test parsing resolved review comments."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        pr_data = {
            "reviewThreads": {
                "nodes": [
                    {
                        "isResolved": True,
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment1",
                                    "body": "Resolved comment",
                                    "createdAt": "2023-01-01T00:00:00Z",
                                    "author": {"login": "user"},
                                    "path": "file.py",
                                    "line": 5,
                                    "originalLine": 5,
                                    "diffHunk": "@@ -5,0 +5,1 @@\n+comment",
                                    "commit": {"oid": "abc123"},
                                }
                            ]
                        },
                    }
                ]
            }
        }

        result = client._parse_review_comments(pr_data)

        assert len(result) == 1
        assert result[0]["resolved"] is True

    def test_parse_review_comments_empty(self, tmp_path):
        """Test parsing empty review comments."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        pr_data = {"reviewThreads": {"nodes": []}}

        result = client._parse_review_comments(pr_data)

        assert result == []

    def test_parse_review_comments_missing_fields(self, tmp_path):
        """Test parsing review comments with missing fields."""
        client = GitHubAPIClient(tmp_path, "owner", "repo")

        pr_data = {
            "reviewThreads": {
                "nodes": [
                    {
                        "isResolved": False,
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment1",
                                    "body": "Comment",
                                    "createdAt": "2023-01-01T00:00:00Z",
                                    "author": None,
                                    "path": "file.py",
                                    "line": None,
                                    "originalLine": None,
                                    "diffHunk": None,
                                    "commit": None,
                                }
                            ]
                        },
                    }
                ]
            }
        }

        result = client._parse_review_comments(pr_data)

        assert len(result) == 1
        assert result[0]["author"] == "unknown"
        assert result[0]["line"] is None
        assert result[0]["original_line"] is None
        assert result[0]["diff_hunk"] is None
        assert result[0]["commit_sha"] is None


class TestFetchPRRest:
    """Test REST API fallback."""

    def test_fetch_pr_rest_success(self, tmp_path):
        """Test successful REST API PR fetching."""
        mock_runner = MockSubprocessRunner()

        # Mock commits response
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=0, stdout="abc123\ndef456"),
        )

        # Mock files response
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=0, stdout="file1.py\nfile2.py"),
        )

        # Mock main PR response
        mock_runner.add_gh_response(
            command="gh pr view 1 --json number,title,url,state,mergedAt,author,body",
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_rest_pr_response(
                    pr_number=1,
                    title="Test PR",
                    state="MERGED",
                    merged=True,
                    author="testuser",
                    body="Test description",
                ),
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_pr_rest(1)

        assert result["number"] == 1
        assert result["title"] == "Test PR"
        assert result["state"] == "merged"
        assert result["merged"] is True
        assert result["author"] == "testuser"
        assert result["commits"] == ["abc123", "def456"]
        assert result["files_changed"] == ["file1.py", "file2.py"]
        assert result["comments"] == []

    def test_fetch_pr_rest_with_commits_and_files(self, tmp_path):
        """Test REST API fetching with commits and files."""
        mock_runner = MockSubprocessRunner()

        # Mock successful responses
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=0, stdout="abc123"),
        )
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=0, stdout="file.py"),
        )
        mock_runner.add_gh_response(
            command="gh pr view 1 --json number,title,url,state,mergedAt,author,body",
            response=MockCompletedProcess(
                returncode=0, stdout=create_rest_pr_response(pr_number=1)
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_pr_rest(1)

        assert result["commits"] == ["abc123"]
        assert result["files_changed"] == ["file.py"]

    def test_fetch_pr_rest_partial_failure(self, tmp_path):
        """Test REST API fetching with partial failure."""
        mock_runner = MockSubprocessRunner()

        # Mock commits failure
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        # Mock files failure
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        # Mock main PR success
        mock_runner.add_gh_response(
            command="gh pr view 1 --json number,title,url,state,mergedAt,author,body",
            response=MockCompletedProcess(
                returncode=0, stdout=create_rest_pr_response(pr_number=1)
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_pr_rest(1)

        assert result["number"] == 1
        assert result["commits"] == []
        assert result["files_changed"] == []

    def test_fetch_pr_rest_complete_failure(self, tmp_path):
        """Test REST API fetching with complete failure."""
        mock_runner = MockSubprocessRunner()

        # Mock all failures
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )
        mock_runner.add_gh_response(
            command="gh pr view 1 --json number,title,url,state,mergedAt,author,body",
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.fetch_pr_rest(1)

        # Should return minimal PR info
        assert result["number"] == 1
        assert result["title"] == "PR #1"
        assert result["url"] == "https://github.com/owner/repo/pull/1"
        assert result["state"] == "unknown"
        assert result["merged"] is False
        assert result["author"] == "unknown"
        assert result["commits"] == []
        assert result["files_changed"] == []
        assert result["comments"] == []


class TestFetchPRCommitsRest:
    """Test commit fetching via REST."""

    def test_fetch_pr_commits_rest_success(self, tmp_path):
        """Test successful commit fetching via REST."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=0, stdout="abc123\ndef456\nghi789"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_commits_rest(1)

        assert result == ["abc123", "def456", "ghi789"]

    def test_fetch_pr_commits_rest_empty(self, tmp_path):
        """Test commit fetching with empty response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_commits_rest(1)

        assert result == []

    def test_fetch_pr_commits_rest_error(self, tmp_path):
        """Test commit fetching with error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "commits", "-q", ".commits[].oid"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_commits_rest(1)

        assert result == []


class TestFetchPRFilesRest:
    """Test file fetching via REST."""

    def test_fetch_pr_files_rest_success(self, tmp_path):
        """Test successful file fetching via REST."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=0, stdout="file1.py\nfile2.py\nfile3.py"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_files_rest(1)

        assert result == ["file1.py", "file2.py", "file3.py"]

    def test_fetch_pr_files_rest_empty(self, tmp_path):
        """Test file fetching with empty response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_files_rest(1)

        assert result == []

    def test_fetch_pr_files_rest_error(self, tmp_path):
        """Test file fetching with error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command=["pr", "view", "1", "--json", "files", "-q", ".files[].path"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client._fetch_pr_files_rest(1)

        assert result == []


class TestGetTotalPRCount:
    """Test PR count estimation."""

    def test_get_total_pr_count_success(self, tmp_path):
        """Test successful PR count estimation."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 1",
            response=MockCompletedProcess(
                returncode=0, stdout=create_pr_list_response(count=1, start_number=150)
            ),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.get_total_pr_count()

        assert result == 150

    def test_get_total_pr_count_empty(self, tmp_path):
        """Test PR count estimation with empty response."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 1",
            response=MockCompletedProcess(returncode=0, stdout=create_empty_response()),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.get_total_pr_count()

        assert result == 0

    def test_get_total_pr_count_error(self, tmp_path):
        """Test PR count estimation with error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_gh_response(
            command="gh pr list --state all --json number --limit 1",
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        client = GitHubAPIClient(tmp_path, "owner", "repo")
        client.runner = mock_runner

        result = client.get_total_pr_count()

        assert result == 0
