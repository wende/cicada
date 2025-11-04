"""Python language support for Cicada using SCIP protocol.

This module provides Python code indexing via scip-python,
which leverages Microsoft's Pyright type checker for semantic analysis.
"""

from cicada.languages.python.indexer import PythonSCIPIndexer

__all__ = ["PythonSCIPIndexer"]
