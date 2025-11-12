"""
Author: Cursor(Auto)

Mock GitHub API responses for testing.

Provides response builders for GitHub API calls that can be customized
for different test scenarios while maintaining realistic data structures.
"""

import json
from typing import Any


def create_pr_list_response(count: int = 5, state: str = "all", start_number: int = 1) -> str:
    """
    Create a mock PR list response.

    Args:
        count: Number of PRs to include
        state: PR state filter
        start_number: Starting PR number

    Returns:
        JSON string of PR list
    """
    prs = []
    for i in range(count):
        prs.append({"number": start_number + i})

    return json.dumps(prs)


def create_graphql_response(
    prs: list[dict[str, Any]] | None = None,
    include_comments: bool = True,
    include_files: bool = True,
    include_commits: bool = True,
) -> str:
    """
    Create a mock GraphQL response for PR batch fetching.

    Args:
        prs: List of PR data dictionaries
        include_comments: Whether to include review comments
        include_files: Whether to include changed files
        include_commits: Whether to include commits

    Returns:
        JSON string of GraphQL response
    """
    if prs is None:
        prs = [create_single_pr_data()]

    # Build repository data with PR queries
    repo_data = {}
    for i, pr in enumerate(prs):
        pr_data = {
            "number": pr.get("number", i + 1),
            "title": pr.get("title", f"Test PR #{i + 1}"),
            "url": pr.get("url", f"https://github.com/owner/repo/pull/{i + 1}"),
            "state": pr.get("state", "MERGED"),
            "mergedAt": pr.get("mergedAt", "2023-01-01T00:00:00Z"),
            "bodyText": pr.get("bodyText", f"Description for PR #{i + 1}"),
            "author": {"login": pr.get("author", "testuser")},
        }

        if include_commits:
            pr_data["commits"] = {
                "nodes": [
                    {"commit": {"oid": f"commit{i}_{j}"}} for j in range(pr.get("commit_count", 2))
                ]
            }
        else:
            pr_data["commits"] = {"nodes": []}

        if include_files:
            pr_data["files"] = {
                "nodes": [{"path": f"file{i}_{j}.py"} for j in range(pr.get("file_count", 3))]
            }
        else:
            pr_data["files"] = {"nodes": []}

        if include_comments:
            pr_data["reviewThreads"] = {
                "nodes": create_review_threads_data(pr.get("comment_count", 2))
            }
        else:
            pr_data["reviewThreads"] = {"nodes": []}

        repo_data[f"pr{i}"] = pr_data

    response = {"data": {"repository": repo_data}}

    return json.dumps(response)


def create_pr_count_graphql_response(total_count: int = 0) -> str:
    """
    Create a mock GraphQL response for PR count query.

    Args:
        total_count: Total number of PRs

    Returns:
        JSON string of GraphQL response
    """
    response = {"data": {"repository": {"pullRequests": {"totalCount": total_count}}}}
    return json.dumps(response)


def create_rest_pr_response(
    pr_number: int = 1,
    title: str = "Test PR",
    state: str = "MERGED",
    merged: bool = True,
    author: str = "testuser",
    body: str = "Test description",
) -> str:
    """
    Create a mock REST API PR response.

    Args:
        pr_number: PR number
        title: PR title
        state: PR state
        merged: Whether PR is merged
        author: PR author
        body: PR description

    Returns:
        JSON string of REST response
    """
    response = {
        "number": pr_number,
        "title": title,
        "url": f"https://github.com/owner/repo/pull/{pr_number}",
        "state": state,
        "mergedAt": "2023-01-01T00:00:00Z" if merged else None,
        "author": {"login": author},
        "body": body,
    }

    return json.dumps(response)


def create_review_comments_response(
    count: int = 3, file_path: str = "test.py", resolved: bool = False
) -> list[dict[str, Any]]:
    """
    Create mock review comment data.

    Args:
        count: Number of comments to create
        file_path: File path for comments
        resolved: Whether comments are resolved

    Returns:
        List of comment dictionaries
    """
    comments = []
    for i in range(count):
        comments.append(
            {
                "id": f"comment_{i}",
                "author": {"login": f"reviewer{i}"},
                "body": f"Review comment {i}",
                "createdAt": "2023-01-01T00:00:00Z",
                "path": file_path,
                "line": 10 + i,
                "originalLine": 10 + i,
                "diffHunk": f"@@ -10,0 +{10 + i},1 @@\n+line {10 + i}",
                "resolved": resolved,
                "commit": {"oid": f"commit_{i}"},
            }
        )

    return comments


def create_single_pr_data(
    number: int = 1,
    title: str = "Test PR",
    state: str = "MERGED",
    author: str = "testuser",
    comment_count: int = 2,
    file_count: int = 3,
    commit_count: int = 2,
) -> dict[str, Any]:
    """
    Create data for a single PR.

    Args:
        number: PR number
        title: PR title
        state: PR state
        author: PR author
        comment_count: Number of review comments
        file_count: Number of changed files
        commit_count: Number of commits

    Returns:
        PR data dictionary
    """
    return {
        "number": number,
        "title": title,
        "state": state,
        "author": author,
        "comment_count": comment_count,
        "file_count": file_count,
        "commit_count": commit_count,
    }


def create_review_threads_data(comment_count: int = 2) -> list[dict[str, Any]]:
    """
    Create mock review thread data.

    Args:
        comment_count: Number of comments per thread

    Returns:
        List of review thread dictionaries
    """
    return [
        {
            "isResolved": False,
            "comments": {"nodes": create_review_comments_response(comment_count)},
        }
    ]


def create_github_error_response(
    message: str = "API rate limit exceeded", status: int = 403
) -> str:
    """
    Create a mock GitHub API error response.

    Args:
        message: Error message
        status: HTTP status code

    Returns:
        JSON string of error response
    """
    response = {"message": message, "documentation_url": "https://docs.github.com/rest"}

    return json.dumps(response)


def create_empty_response() -> str:
    """
    Create an empty JSON response.

    Returns:
        JSON string of empty array
    """
    return json.dumps([])


def create_null_response() -> str:
    """
    Create a null response.

    Returns:
        String "null"
    """
    return "null"


def create_malformed_json_response() -> str:
    """
    Create malformed JSON for testing error handling.

    Returns:
        Malformed JSON string
    """
    return '{"incomplete": "json"'


# Complex scenario builders


def create_large_pr_batch_response(
    pr_count: int = 10, comments_per_pr: int = 5, files_per_pr: int = 8
) -> str:
    """
    Create a large batch of PRs for performance testing.

    Args:
        pr_count: Number of PRs
        comments_per_pr: Comments per PR
        files_per_pr: Files per PR

    Returns:
        JSON string of large GraphQL response
    """
    prs = []
    for i in range(pr_count):
        prs.append(
            create_single_pr_data(
                number=i + 1, comment_count=comments_per_pr, file_count=files_per_pr
            )
        )

    return create_graphql_response(prs)


def create_pr_with_complex_comments() -> str:
    """
    Create a PR with complex comment structure.

    Returns:
        JSON string of GraphQL response with complex comments
    """
    pr_data = create_single_pr_data(comment_count=10)

    # Create complex review threads
    complex_threads = [
        {
            "isResolved": True,
            "comments": {"nodes": create_review_comments_response(3, "resolved_file.py", True)},
        },
        {
            "isResolved": False,
            "comments": {"nodes": create_review_comments_response(2, "active_file.py", False)},
        },
    ]

    pr_data["reviewThreads"] = {"nodes": complex_threads}

    return create_graphql_response([pr_data])


def create_pr_with_no_metadata() -> str:
    """
    Create a PR response with missing metadata fields.

    Returns:
        JSON string of GraphQL response with missing fields
    """
    pr_data = {
        "number": 1,
        "title": "Minimal PR",
        "url": "https://github.com/owner/repo/pull/1",
        "state": "OPEN",
        "mergedAt": None,
        "bodyText": "",
        "author": None,
        "commits": {"nodes": []},
        "files": {"nodes": []},
        "reviewThreads": {"nodes": []},
    }

    response = {"data": {"repository": {"pr0": pr_data}}}

    return json.dumps(response)
