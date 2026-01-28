"""
Cicada Core - Shared foundation for Cicada code intelligence.

This module provides:
- BaseIndexer: Abstract base class for all language indexers
- BaseLanguageFormatter: Abstract base class for language formatters
- Storage utilities: Path management for index files
- Hash utilities: File hashing for incremental indexing
"""

from cicada.core.base_indexer import BaseIndexer
from cicada.core.hash_utils import (
    compute_file_hash,
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada.core.storage import (
    create_storage_dir,
    get_config_path,
    get_hashes_path,
    get_index_path,
    get_repo_hash,
    get_storage_dir,
)
from cicada.languages.formatter_interface import BaseLanguageFormatter

__all__ = [
    # Base classes
    "BaseIndexer",
    "BaseLanguageFormatter",
    # Hash utilities
    "compute_file_hash",
    "compute_hashes_for_files",
    "detect_file_changes",
    "load_file_hashes",
    "save_file_hashes",
    # Storage utilities
    "get_repo_hash",
    "get_storage_dir",
    "create_storage_dir",
    "get_index_path",
    "get_config_path",
    "get_hashes_path",
]
