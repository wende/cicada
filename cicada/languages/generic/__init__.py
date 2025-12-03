"""
Generic file indexer for text files not handled by language-specific indexers.

This module provides the GenericFileIndexer which indexes all text files
(markdown, config files, docs, etc.) that are not already covered by
language-specific indexers like Elixir, Python, or Erlang.
"""

from cicada.languages.generic.indexer import GenericFileIndexer

__all__ = ["GenericFileIndexer"]
