"""
Generic language tooling.

Exports the GenericFileIndexer used for text-only files plus helper utilities
to run the generic pass after language-specific indexers.
"""

from .indexer import (
    GenericFileIndexer,
    run_generic_indexing,
    run_generic_indexing_for_language_indexer,
)

__all__ = [
    "GenericFileIndexer",
    "run_generic_indexing",
    "run_generic_indexing_for_language_indexer",
]
