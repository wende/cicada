"""
Cicada Core - Shared foundation for Cicada code intelligence packages.

This package provides:
- BaseIndexer: Abstract base class for all language indexers
- BaseLanguageFormatter: Abstract base class for language formatters
- Storage utilities: Path management for index files
- Hash utilities: File hashing for incremental indexing
"""

from cicada_mcp_core.base_indexer import BaseIndexer
from cicada_mcp_core.formatter_interface import BaseLanguageFormatter

__version__ = "0.1.0"
__all__ = ["BaseIndexer", "BaseLanguageFormatter"]
