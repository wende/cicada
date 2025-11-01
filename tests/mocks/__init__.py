"""
Author: Cursor(Auto)

Mock infrastructure for PR indexer tests.

This module provides reusable, implementation-agnostic mocks for testing
GitHubAPIClient and LineMapper components.
"""

from .git_responses import (
    create_file_content_response,
    create_git_ls_files_response,
    create_git_show_response,
)
from .github_responses import (
    create_graphql_response,
    create_pr_list_response,
    create_rest_pr_response,
    create_review_comments_response,
)
from .subprocess_mocks import MockCompletedProcess, MockSubprocessRunner

__all__ = [
    "MockSubprocessRunner",
    "MockCompletedProcess",
    "create_pr_list_response",
    "create_graphql_response",
    "create_rest_pr_response",
    "create_review_comments_response",
    "create_file_content_response",
    "create_git_show_response",
    "create_git_ls_files_response",
]
