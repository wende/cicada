"""
Embeddings module for semantic code search.

This module provides embeddings-based indexing and search using cicada-vector.
Imports are lazy to avoid crashing when cicada-vector is outdated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cicada.embeddings.indexer import EmbeddingsIndexer as EmbeddingsIndexer
    from cicada.embeddings.searcher import EmbeddingsSearcher as EmbeddingsSearcher


def __getattr__(name: str):
    if name == "EmbeddingsIndexer":
        from cicada.embeddings.indexer import EmbeddingsIndexer

        return EmbeddingsIndexer
    if name == "EmbeddingsSearcher":
        from cicada.embeddings.searcher import EmbeddingsSearcher

        return EmbeddingsSearcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["EmbeddingsIndexer", "EmbeddingsSearcher"]
