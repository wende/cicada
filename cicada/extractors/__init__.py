"""
Extractors for parsing Elixir source code.

This package contains specialized extractors for different parts of Elixir modules.

Author: Cursor(Auto)
"""

from .module import extract_modules
from .function import extract_functions
from .spec import extract_specs, match_specs_to_functions
from .doc import extract_docs, match_docs_to_functions
from .dependency import (
    extract_aliases,
    extract_imports,
    extract_requires,
    extract_uses,
    extract_behaviours,
)
from .call import extract_function_calls, extract_value_mentions

__all__ = [
    "extract_modules",
    "extract_functions",
    "extract_specs",
    "match_specs_to_functions",
    "extract_docs",
    "match_docs_to_functions",
    "extract_aliases",
    "extract_imports",
    "extract_requires",
    "extract_uses",
    "extract_behaviours",
    "extract_function_calls",
    "extract_value_mentions",
]
