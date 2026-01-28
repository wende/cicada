"""Utilities for cicada-core."""

from cicada_mcp_core.utils.hash_utils import (
    compute_file_hash,
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada_mcp_core.utils.storage import (
    create_storage_dir,
    get_config_path,
    get_hashes_path,
    get_index_path,
    get_repo_hash,
    get_storage_dir,
)

__all__ = [
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
