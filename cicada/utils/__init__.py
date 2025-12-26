"""
Utility modules for CICADA.

This package contains shared utilities used across the codebase to reduce
code duplication and improve maintainability.
"""

from .call_site_formatter import CallSiteFormatter
from .function_grouper import FunctionGrouper
from .fuzzy_match import find_similar_names
from .index_utils import (
    load_index,
    merge_indexes_incremental,
    save_index,
    validate_index_structure,
)
from .path_utils import is_git_repository, normalize_file_path, resolve_to_repo_root
from .signature_builder import SignatureBuilder
from .storage import (
    create_storage_dir,
    get_config_path,
    get_embeddings_path,
    get_hashes_path,
    get_index_path,
    get_pr_index_path,
    get_repo_hash,
    get_storage_dir,
)
from .subprocess_runner import SubprocessRunner, run_gh_command, run_git_command
from .text_utils import extract_code_identifiers, split_camel_snake_case, split_identifier
from .tree_utils import extract_text_from_node, is_function_definition_call

__all__ = [
    "SubprocessRunner",
    "run_git_command",
    "run_gh_command",
    "normalize_file_path",
    "resolve_to_repo_root",
    "is_git_repository",
    "load_index",
    "save_index",
    "merge_indexes_incremental",
    "validate_index_structure",
    "FunctionGrouper",
    "CallSiteFormatter",
    "SignatureBuilder",
    "find_similar_names",
    "split_identifier",
    "split_camel_snake_case",
    "extract_code_identifiers",
    "get_repo_hash",
    "get_storage_dir",
    "create_storage_dir",
    "get_index_path",
    "get_config_path",
    "get_embeddings_path",
    "get_hashes_path",
    "get_pr_index_path",
    "extract_text_from_node",
    "is_function_definition_call",
]
