"""
Utility modules for CICADA.

This package contains shared utilities used across the codebase to reduce
code duplication and improve maintainability.
"""

from .subprocess_runner import SubprocessRunner, run_git_command, run_gh_command
from .path_utils import normalize_file_path, resolve_to_repo_root
from .index_utils import load_index, save_index
from .function_grouper import FunctionGrouper
from .call_site_formatter import CallSiteFormatter
from .signature_builder import SignatureBuilder

__all__ = [
    "SubprocessRunner",
    "run_git_command",
    "run_gh_command",
    "normalize_file_path",
    "resolve_to_repo_root",
    "load_index",
    "save_index",
    "FunctionGrouper",
    "CallSiteFormatter",
    "SignatureBuilder",
]
