"""SCIP support for Cicada - re-exports from cicada_scip package.

This module re-exports classes from the new cicada_scip package
for backward compatibility during the monorepo migration.

SCIP is a language-agnostic protocol created by Sourcegraph for code intelligence.
Learn more: https://github.com/sourcegraph/scip

Note: cicada_scip is an optional dependency. If not installed, SCIP-based
language indexers will not be available.
"""

__all__ = []
SCIP_AVAILABLE = False
SCIP_IMPORT_ERROR: str | None = None

try:
    # Re-export from new package for backward compatibility
    from cicada_scip import GenericSCIPIndexer, SCIPConverter, SCIPReader, scip_pb2
    from cicada_scip.converter import CallSite, DocumentData, ImportData, SymbolData
    from cicada_scip.formatter import (
        CFormatter,
        CppFormatter,
        CSharpFormatter,
        DartFormatter,
        GoFormatter,
        JavaFormatter,
        JavaScriptFormatter,
        PythonFormatter,
        RubyFormatter,
        RustFormatter,
        ScalaFormatter,
        SCIPFormatter,
        TypeScriptFormatter,
        VBFormatter,
    )

    __all__ = [
        "SCIPReader",
        "SCIPConverter",
        "GenericSCIPIndexer",
        "DocumentData",
        "SymbolData",
        "CallSite",
        "ImportData",
        "SCIPFormatter",
        "PythonFormatter",
        "TypeScriptFormatter",
        "JavaScriptFormatter",
        "GoFormatter",
        "RustFormatter",
        "JavaFormatter",
        "ScalaFormatter",
        "CFormatter",
        "CppFormatter",
        "CSharpFormatter",
        "VBFormatter",
        "RubyFormatter",
        "DartFormatter",
        "scip_pb2",
        "SCIP_AVAILABLE",
        "SCIP_IMPORT_ERROR",
    ]

    SCIP_AVAILABLE = True

except ImportError as e:
    # Capture the error for diagnostic purposes
    SCIP_IMPORT_ERROR = str(e)
