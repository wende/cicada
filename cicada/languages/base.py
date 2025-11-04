"""
Base classes for language implementations.

This module re-exports the abstract base classes from cicada.parsing for convenience.
Language implementations should inherit from these classes.
"""

from cicada.parsing.base_indexer import BaseIndexer
from cicada.parsing.base_parser import BaseParser
from cicada.parsing.language_config import LanguageConfig

__all__ = ["BaseParser", "BaseIndexer", "LanguageConfig"]
