"""
Utility modules for CICADA.

This package contains shared utilities used across the codebase to reduce
code duplication and improve maintainability.
"""

from .call_site_formatter import CallSiteFormatter
from .function_grouper import FunctionGrouper
from .index_utils import (
    load_index,
    merge_indexes_incremental,
    save_index,
    validate_index_structure,
)
from .path_utils import normalize_file_path, resolve_to_repo_root
from .signature_builder import SignatureBuilder
from .storage import (
    create_storage_dir,
    get_config_path,
    get_hashes_path,
    get_index_path,
    get_pr_index_path,
    get_repo_hash,
    get_storage_dir,
)
from .subprocess_runner import SubprocessRunner, run_gh_command, run_git_command
from .text_utils import split_camel_snake_case, split_identifier

__all__ = [
    "SubprocessRunner",
    "run_git_command",
    "run_gh_command",
    "normalize_file_path",
    "resolve_to_repo_root",
    "load_index",
    "save_index",
    "merge_indexes_incremental",
    "validate_index_structure",
    "FunctionGrouper",
    "CallSiteFormatter",
    "SignatureBuilder",
    "split_identifier",
    "split_camel_snake_case",
    "get_repo_hash",
    "get_storage_dir",
    "create_storage_dir",
    "get_index_path",
    "get_config_path",
    "get_hashes_path",
    "get_pr_index_path",
]
