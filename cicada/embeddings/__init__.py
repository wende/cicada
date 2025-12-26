"""
Embeddings module for semantic code search.

This module provides embeddings-based indexing and search using cicada-vector.
"""

from cicada.embeddings.indexer import EmbeddingsIndexer
from cicada.embeddings.searcher import EmbeddingsSearcher

__all__ = ["EmbeddingsIndexer", "EmbeddingsSearcher"]
