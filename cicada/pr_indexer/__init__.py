"""
PR Indexer package.

This package contains classes for indexing GitHub pull requests,
separated by responsibility for better maintainability.
"""

from .github_api_client import GitHubAPIClient
from .pr_index_builder import PRIndexBuilder
from .line_mapper import LineMapper
from .indexer import PRIndexer
from .cli import main

__all__ = [
    "GitHubAPIClient",
    "PRIndexBuilder",
    "LineMapper",
    "PRIndexer",
    "main",
]
