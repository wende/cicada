"""
Universal parsing infrastructure for multi-language support.

This module provides abstract base classes and utilities that all language
implementations must follow.
"""

from cicada.parsing.base_indexer import BaseIndexer
from cicada.parsing.base_parser import BaseParser
from cicada.parsing.language_config import LanguageConfig
from cicada.parsing.schema import FunctionData, ModuleData, UniversalIndexSchema

__all__ = [
    "BaseParser",
    "BaseIndexer",
    "UniversalIndexSchema",
    "ModuleData",
    "FunctionData",
    "LanguageConfig",
]
