"""Convert SCIP Index to Cicada's UniversalIndexSchema.

This module handles the mapping from SCIP protocol buffer format to
Cicada's JSON index format.
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cicada.languages.scip.scip_pb2 as scip_pb2

# Lazy imports for symbol_types modules to avoid circular imports
# These are imported at module load time but after the class is defined
_python_symbols = None
_typescript_symbols = None


def _get_python_symbols():
    """Lazy import for Python symbol types module."""
    global _python_symbols
    if _python_symbols is None:
        import cicada.languages.python.symbol_types as ps

        _python_symbols = ps
    return _python_symbols


def _get_typescript_symbols():
    """Lazy import for TypeScript symbol types module."""
    global _typescript_symbols
    if _typescript_symbols is None:
        import cicada.languages.typescript.symbol_types as ts

        _typescript_symbols = ts
    return _typescript_symbols


@dataclass
class SymbolData:
    """Metadata for a single SCIP symbol (class, function, method, etc.)."""

    symbol: str
    symbol_type: str  # 'class', 'function', 'method', 'parameter', etc.
    line: int
    doc: str = ""
    arity: int = 0  # For functions/methods
    parent_symbol: str | None = None  # For methods (points to class)


@dataclass
class CallSite:
    """A function call occurrence."""

    callee_symbol: str
    line: int
    caller_symbol: str | None = None  # Set during processing


@dataclass
class ImportData:
    """An import/dependency."""

    module: str
    symbols: list[str]
    line: int


@dataclass
class DocumentData:
    """Intermediate format for one file's extracted SCIP data."""

    relative_path: str
    aliases: dict[str, str]
    symbols: dict[str, SymbolData]  # symbol -> SymbolData
    function_ranges: list[tuple[int, int, str]]  # (start_line, end_line, symbol)
    function_start_lines: list[int]  # Pre-computed for binary search
    call_sites: list[CallSite]
    dependencies: list[ImportData]


class SCIPConverter:
    """Convert SCIP Index to Cicada's UniversalIndexSchema."""

    def __init__(
        self,
        extract_keywords: bool = False,
        keyword_extractor=None,
        extract_references: bool = True,
        verbose: bool = False,
        import_search_lines: int = 50,
    ):
        """
        Initialize SCIP converter.

        Args:
            extract_keywords: If True, extract keywords from documentation
            keyword_extractor: Keyword extractor instance (LightweightKeywordExtractor or KeyBERTExtractor)
            extract_references: If True, extract call sites and references from SCIP occurrences (default: True)
            verbose: If True, print progress messages
            import_search_lines: Number of lines to search for imports (default: 50).
                                 Increased from 15 to handle files with large docstrings/headers.
        """
        self.extract_keywords = extract_keywords
        self.keyword_extractor = keyword_extractor
        self.extract_references = extract_references
        self.verbose = verbose
        self.import_search_lines = import_search_lines

    def convert(self, scip_index: scip_pb2.Index, repo_path: Path) -> dict:
        """
        Convert SCIP Index to Cicada index format using two-phase architecture.

        Phase 1: Extract all data in single pass per document (O(n))
        Phase 2: Process extracted data to build modules (O(n))

        This replaces the old O(n²) approach that had nested occurrence loops.

        Args:
            scip_index: Parsed SCIP protobuf
            repo_path: Repository root path

        Returns:
            Dict in UniversalIndexSchema format with 'modules' and 'metadata' keys
        """
        modules = {}

        # Build a symbol lookup map for quick access
        symbol_map = self._build_symbol_map(scip_index)

        # THREE-PHASE PROCESSING
        # Phase 1: Extract all SCIP data for all documents (builds arity info)
        all_doc_data = []
        global_arity_map: dict[str, int] = {}

        for doc in scip_index.documents:
            doc_data = self._extract_document_data(doc, repo_path)
            all_doc_data.append(doc_data)

            # Build global arity map from all symbols across all documents
            for symbol, symbol_data in doc_data.symbols.items():
                if symbol_data.arity > 0:
                    global_arity_map[symbol] = symbol_data.arity

        # Phase 1.5: Enrich arity map with docstring-derived arities
        # SCIP may not emit parameter occurrences for all functions, but docstrings
        # often contain signatures. Update arity map for functions that have arity 0
        # from parameter occurrences but have signature info in documentation.
        for doc_data in all_doc_data:
            for symbol, symbol_data in doc_data.symbols.items():
                # Only process functions/methods without arity from parameter occurrences
                is_func_or_method = symbol_data.symbol_type in ("function", "method")
                needs_arity = symbol not in global_arity_map or global_arity_map[symbol] == 0
                if is_func_or_method and needs_arity:
                    # Try to extract arity from docstring
                    symbol_info = symbol_map.get(symbol)
                    if symbol_info and symbol_info.documentation:
                        raw_doc = "\n".join(symbol_info.documentation)
                        _, _, args = self._parse_signature_from_doc(raw_doc)
                        if args:
                            global_arity_map[symbol] = len(args)

        # Phase 2: Process extracted data to build modules (with global arity map)
        for doc_data in all_doc_data:
            file_modules = self._process_document_data(doc_data, symbol_map, global_arity_map)
            modules.update(file_modules)

        # Phase 3: Build reverse call index for O(1) "what calls this" queries
        reverse_calls = self._build_reverse_call_index(modules)

        # Build metadata
        metadata = self._build_metadata(scip_index, repo_path, len(modules))

        result = {"modules": modules, "metadata": metadata}
        if reverse_calls:
            result["reverse_calls"] = reverse_calls
        return result

    def _build_symbol_map(self, scip_index: scip_pb2.Index) -> dict:
        """Build a map of symbol -> SymbolInformation for quick lookup."""
        symbol_map = {}
        for doc in scip_index.documents:
            for symbol_info in doc.symbols:
                symbol_map[symbol_info.symbol] = symbol_info
        return symbol_map

    def _extract_aliases(self, doc: scip_pb2.Document, repo_path: Path) -> dict[str, str]:
        """
        Extract import aliases from Python source file.

        Args:
            doc: SCIP Document
            repo_path: Repository root

        Returns:
            Dictionary mapping alias names to full module names
        """
        try:
            from cicada.languages.python.alias_extractor import PythonAliasExtractor

            full_path = repo_path / doc.relative_path
            alias_extractor = PythonAliasExtractor()
            aliases = alias_extractor.extract_aliases(full_path)
            return aliases
        except Exception as e:
            if self.verbose:
                print(
                    f"Warning: Failed to extract aliases from {doc.relative_path}: {e}",
                    file=sys.stderr,
                )
            return {}

    def _process_definition(
        self,
        occurrence,
        symbol: str,
        line: int,
        symbol_type: str,
        symbols: dict,
        function_ranges: list,
        param_counts: dict,
    ) -> None:
        """
        Process a definition occurrence and update data structures.

        Args:
            occurrence: SCIP occurrence object
            symbol: SCIP symbol string
            line: Line number (1-indexed)
            symbol_type: Type of symbol (class, function, method, etc.)
            symbols: Dictionary to store symbol metadata
            function_ranges: List to store function line ranges
            param_counts: Dictionary to track parameter counts per function
        """
        # Extract documentation (skip for test functions)
        doc_text = ""
        if occurrence.symbol_roles & scip_pb2.SymbolRole.Test:
            doc_text = ""

        # Store symbol metadata for relevant types
        if symbol_type in ("class", "function", "method", "module", "parameter"):
            # Get parent for methods
            parent_symbol = None
            if symbol_type == "method":
                parent_symbol = self._get_parent_symbol(symbol)

            symbols[symbol] = SymbolData(
                symbol=symbol,
                symbol_type=symbol_type,
                line=line,
                doc=doc_text,
                arity=0,  # Will be computed from param_counts
                parent_symbol=parent_symbol,
            )

            # Build function ranges for binary search
            if symbol_type in ("function", "method"):
                if occurrence.enclosing_range and len(occurrence.enclosing_range) >= 3:
                    start_line = occurrence.enclosing_range[0] + 1
                    end_line = occurrence.enclosing_range[2] + 1
                    function_ranges.append((start_line, end_line, symbol))
                elif occurrence.range:
                    # Fallback: use definition line with reasonable upper bound
                    start_line = occurrence.range[0] + 1
                    function_ranges.append((start_line, 10000, symbol))

            # Count parameters: increment parent function's param count
            if symbol_type == "parameter":
                parent_func = self._extract_function_from_parameter(symbol)
                if parent_func:
                    param_counts[parent_func] = param_counts.get(parent_func, 0) + 1

    def _process_call_site(
        self,
        symbol: str,
        line: int,
        call_sites: list,
    ) -> None:
        """
        Process a call site occurrence.

        Args:
            symbol: SCIP symbol string
            line: Line number (1-indexed)
            call_sites: List to store call site data
        """
        if not self.extract_references:
            return

        # Use language-aware symbol type detection to identify callables
        symbol_type = self._get_symbol_type(symbol)
        if symbol_type in ("function", "method"):
            call_sites.append(
                CallSite(
                    callee_symbol=symbol,
                    line=line,
                    caller_symbol=None,  # Will be set later via binary search
                )
            )

    def _process_import(
        self,
        symbol: str,
        line: int,
        dependencies: list,
        imports_by_line: dict,
        seen_imports: set,
    ) -> None:
        """
        Process an import statement occurrence.

        Args:
            symbol: SCIP symbol string
            line: Line number (1-indexed)
            dependencies: List to store import data
            imports_by_line: Dictionary to group multi-symbol imports
            seen_imports: Set to track already-seen module imports
        """
        # Only process imports within the search range
        if line > self.import_search_lines:
            return

        module_name = self._extract_module_from_symbol(symbol)
        if not module_name or self._is_builtin_module(module_name):
            return

        is_module_import = symbol.endswith(":")

        if is_module_import:
            # Module-level import: "import foo"
            if module_name not in seen_imports:
                dependencies.append(
                    ImportData(
                        module=module_name,
                        symbols=[],
                        line=line,
                    )
                )
                seen_imports.add(module_name)
        else:
            # Symbol import: "from foo import bar"
            if line not in imports_by_line:
                imports_by_line[line] = ImportData(
                    module=module_name,
                    symbols=[],
                    line=line,
                )

            # Extract and add symbol name
            symbol_name = self._extract_name(symbol)
            if symbol_name and symbol_name not in imports_by_line[line].symbols:
                imports_by_line[line].symbols.append(symbol_name)

    def _extract_document_data(self, doc: scip_pb2.Document, repo_path: Path) -> DocumentData:
        """
        Phase 1: Extract all SCIP data in a single pass.

        This method replaces the O(n²) nested loops with a single-pass extraction,
        dramatically improving performance from 1325s to ~10s for 268 files.

        Key optimizations:
        - Single loop through occurrences per document
        - Pre-count parameters during first pass (no O(n²) loop in _get_function_arity!)
        - Pre-build function ranges for O(log n) binary search
        - Match call sites to functions using binary search

        Args:
            doc: SCIP Document
            repo_path: Repository root

        Returns:
            DocumentData with all extracted information
        """
        # Extract import aliases from source file
        aliases = self._extract_aliases(doc, repo_path)

        # Initialize data structures
        symbols = {}  # symbol -> SymbolData
        function_ranges = []  # [(start_line, end_line, symbol), ...]
        call_sites = []  # [CallSite, ...]
        dependencies = []  # [ImportData, ...]
        param_counts = {}  # function_symbol -> parameter count

        # Track imports by line to group multi-symbol imports
        imports_by_line = {}
        seen_imports = set()

        # SINGLE PASS through ALL occurrences
        for occurrence in doc.occurrences:
            symbol = occurrence.symbol
            is_definition = bool(occurrence.symbol_roles & scip_pb2.SymbolRole.Definition)
            is_read_access = bool(occurrence.symbol_roles & scip_pb2.SymbolRole.ReadAccess)

            # Get line number (convert from 0-indexed to 1-indexed)
            line = (occurrence.range[0] + 1) if occurrence.range else 0
            if line == 0:
                continue

            # Determine symbol type ONCE per occurrence
            symbol_type = self._get_symbol_type(symbol)

            # Handle definitions
            if is_definition:
                self._process_definition(
                    occurrence, symbol, line, symbol_type, symbols, function_ranges, param_counts
                )

            # Handle call sites and imports (non-definitions)
            # Note: scip-typescript doesn't set ReadAccess for function calls,
            # so we also check for non-definition callable symbols
            is_callable_reference = not is_definition and symbol_type in ("function", "method")
            if is_read_access and not is_definition:
                # Process import statements (requires ReadAccess)
                self._process_import(symbol, line, dependencies, imports_by_line, seen_imports)

            # Process call sites - either ReadAccess OR callable reference
            if (is_read_access or is_callable_reference) and not is_definition:
                self._process_call_site(symbol, line, call_sites)

        # Consolidate imports from imports_by_line
        dependencies.extend(imports_by_line.values())

        # Update function arities from param_counts
        for func_symbol, count in param_counts.items():
            if func_symbol in symbols:
                symbols[func_symbol].arity = count

        # Sort function ranges by start line for binary search
        function_ranges.sort(key=lambda x: x[0])

        # Fix fallback ranges: replace placeholder upper bounds with next sibling's start
        # This handles functions without enclosing_range that used a fallback upper bound
        # IMPORTANT: Skip nested functions (whose symbols start with current function's symbol)
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:  # Fallback upper bound was used
                # Find next sibling function (not a nested child)
                # Nested functions have symbols that start with the parent's symbol
                sibling_start = None
                for j in range(i + 1, len(function_ranges)):
                    next_symbol = function_ranges[j][2]
                    # A nested function's symbol starts with the parent's symbol
                    # e.g., "module.outer().inner()." starts with "module.outer()."
                    if not next_symbol.startswith(symbol):
                        sibling_start = function_ranges[j][0]
                        break

                if sibling_start is not None:
                    # Use sibling function's start line - 1 as the upper bound
                    function_ranges[i] = (start, sibling_start - 1, symbol)
                else:
                    # No sibling found: use a very large line number
                    function_ranges[i] = (start, 999999, symbol)

                if self.verbose:
                    print(f"  Warning: No enclosing_range for {symbol}, using fallback range")

        # Pre-compute start_lines list for binary search (performance optimization)
        function_start_lines = [start for start, _, _ in function_ranges]

        # Match call sites to enclosing functions using FAST binary search
        # Only if extract_references is enabled
        if self.extract_references:
            for call in call_sites:
                call.caller_symbol = self._find_enclosing_fast(
                    call.line, function_ranges, function_start_lines
                )

        return DocumentData(
            relative_path=doc.relative_path,
            aliases=aliases,
            symbols=symbols,
            function_ranges=function_ranges,
            function_start_lines=function_start_lines,
            call_sites=call_sites,
            dependencies=dependencies,
        )

    def _extract_function_from_parameter(self, parameter_symbol: str) -> str | None:
        """
        Extract parent function symbol from parameter symbol.

        Parameter symbols have format: "function_symbol.(param_name)"
        For example: "scip-python python pkg ver module/func().(param)"

        Args:
            parameter_symbol: SCIP parameter symbol

        Returns:
            Parent function symbol, or None if extraction fails
        """
        # Find the ".(" that marks the parameter
        idx = parameter_symbol.rfind(".(")
        if idx == -1:
            return None

        # Everything before ".(" is the function symbol (should end with "().")
        # After rfind(".("), we get the symbol without the trailing dot, e.g. "func()"
        # We need to add just "." to make it "func()."
        func_symbol = parameter_symbol[:idx]
        if func_symbol.endswith("()"):
            func_symbol += "."
        elif not func_symbol.endswith("()."):
            func_symbol += "()."

        return func_symbol

    def _find_enclosing_fast(
        self,
        line: int,
        function_ranges: list[tuple[int, int, str]],
        function_start_lines: list[int],
    ) -> str | None:
        """
        Find enclosing function using binary search on pre-sorted ranges.

        This uses O(log n) binary search on pre-computed start lines, then checks
        nearby candidates for the smallest enclosing range (for nested functions).

        Args:
            line: Line number to check
            function_ranges: Sorted list of (start_line, end_line, symbol) tuples
            function_start_lines: Pre-computed list of start lines (for binary search)

        Returns:
            Symbol of enclosing function, or None if not in a function
        """
        import bisect

        if not function_ranges:
            return None

        # Binary search for the rightmost function that starts at or before line
        idx = bisect.bisect_right(function_start_lines, line) - 1

        # If line is before all functions, no enclosing function exists
        if idx < 0:
            return None

        # When multiple functions have the same start_line, bisect_right gives us
        # the last one. We need to check all functions with that start_line.
        # Walk backwards to find the first function with the same start_line.
        target_start = function_start_lines[idx]
        first_idx = idx
        while first_idx > 0 and function_start_lines[first_idx - 1] == target_start:
            first_idx -= 1

        # Check candidates (functions that might contain this line)
        # For nested functions, find the smallest enclosing range
        best_match = None
        best_range_size = float("inf")

        # Check forward from first_idx for functions whose start_line <= line
        for i in range(first_idx, len(function_ranges)):
            start, end, symbol = function_ranges[i]

            # If this function starts after line, no more candidates going forward
            if start > line:
                break

            # Check if line is within this function's range
            if start <= line <= end:
                range_size = end - start
                if range_size < best_range_size:
                    best_match = symbol
                    best_range_size = range_size

        # Also check backward from first_idx for outer functions that might contain the line
        # This handles nested functions where an outer function at a lower index
        # has a range that extends past inner functions
        for i in range(first_idx - 1, -1, -1):
            start, end, symbol = function_ranges[i]

            # If this function ends before line, skip it
            if end < line:
                continue

            # Check if line is within this function's range
            if start <= line <= end:
                range_size = end - start
                if range_size < best_range_size:
                    best_match = symbol
                    best_range_size = range_size

        return best_match

    def _process_document_data(
        self,
        doc_data: DocumentData,
        symbol_map: dict,
        global_arity_map: dict[str, int] | None = None,
    ) -> dict:
        """
        Phase 2: Process intermediate data to build Cicada modules.

        This method operates on the pre-extracted DocumentData and doesn't
        access SCIP occurrences, making it much faster (simple dict operations).

        Args:
            doc_data: Pre-extracted document data from Phase 1
            symbol_map: Symbol lookup map for documentation
            global_arity_map: Global map of symbol -> arity for cross-file resolution

        Returns:
            Dict mapping module names to ModuleData dicts
        """
        modules = {}

        # Group symbols by type
        classes = []
        functions = []
        methods_by_class = {}  # class_symbol -> [method symbols]

        for symbol_data in doc_data.symbols.values():
            if symbol_data.symbol_type == "class":
                classes.append(symbol_data)
            elif symbol_data.symbol_type == "function":
                functions.append(symbol_data)
            elif symbol_data.symbol_type == "method" and symbol_data.parent_symbol:
                methods_by_class.setdefault(symbol_data.parent_symbol, []).append(symbol_data)

        # Group call sites by caller function
        call_sites_by_function = {}
        for call_site in doc_data.call_sites:
            if call_site.caller_symbol:
                call_sites_by_function.setdefault(call_site.caller_symbol, []).append(
                    {
                        "callee": call_site.callee_symbol,
                        "file": doc_data.relative_path,
                        "line": call_site.line,
                    }
                )

        # Track class metadata for module-level tracking
        class_metadata_list = []

        # Build class modules
        for class_data in classes:
            class_name = self._extract_name(class_data.symbol)
            class_methods = methods_by_class.get(class_data.symbol, [])

            # Count public/private methods
            public_count = sum(1 for m in class_methods if not self._is_private(m.symbol))
            private_count = sum(1 for m in class_methods if self._is_private(m.symbol))

            # Build function entries for methods
            function_entries = []
            for method_data in class_methods:
                func_entry = self._build_function_entry(
                    method_data,
                    doc_data,
                    symbol_map,
                    call_sites_by_function,
                    global_arity_map,
                )
                function_entries.append(func_entry)

            # Aggregate all calls from function entries for module-level tracking
            module_calls = []
            for func_entry in function_entries:
                module_calls.extend(func_entry.get("dependencies", []))

            # Create class module
            module_data = {
                "file": doc_data.relative_path,
                "line": class_data.line,
                "functions": function_entries,
                "calls": module_calls,
                "dependencies": self._merge_dependencies_to_dict(doc_data.dependencies),
                "aliases": doc_data.aliases,
                "imports": [dep.module for dep in doc_data.dependencies],
            }

            # Add documentation
            symbol_info = symbol_map.get(class_data.symbol)
            if symbol_info and symbol_info.documentation:
                module_data["moduledoc"] = "\n".join(symbol_info.documentation)

            # Extract keywords if enabled
            if self.extract_keywords and self.keyword_extractor:
                module_doc = module_data.get("moduledoc", "")
                func_docs = " ".join(f.get("doc", "") for f in function_entries)
                combined_text = f"{module_doc} {func_docs}".strip()
                if combined_text:
                    keywords = self._normalize_keywords(
                        self.keyword_extractor.extract_keywords(combined_text)
                    )
                    if keywords:
                        module_data["keywords"] = keywords
                # Also extract keywords for individual functions
                for func_entry in function_entries:
                    func_doc = func_entry.get("doc", "")
                    if func_doc:
                        func_keywords = self._normalize_keywords(
                            self.keyword_extractor.extract_keywords(func_doc)
                        )
                        if func_keywords:
                            func_entry["keywords"] = func_keywords

            # Store metadata for parent module
            class_metadata_list.append(
                {
                    "name": class_name,
                    "line": class_data.line,
                    "public_count": public_count,
                    "private_count": private_count,
                    "doc": module_data.get("moduledoc", ""),
                }
            )

            # Add module name and type
            full_class_name = self._build_module_name(class_data.symbol)
            module_data["name"] = full_class_name
            module_data["type"] = "class"
            module_data["parent_module"] = self._get_file_module_name(doc_data.relative_path)

            # Set module_kind from SCIP SymbolInformation.kind, with moduledoc fallback
            module_kind = "unknown"
            if symbol_info and hasattr(symbol_info, "kind"):
                module_kind = self._scip_kind_to_module_kind(symbol_info.kind)

            # If SCIP kind is unknown/unspecified, try parsing moduledoc
            if module_kind == "unknown":
                moduledoc = module_data.get("moduledoc", "")
                module_kind = self._extract_module_kind_from_moduledoc(moduledoc)

            # Final fallback to "class" for class-type modules
            if module_kind == "unknown":
                module_kind = "class"

            module_data["module_kind"] = module_kind

            modules[full_class_name] = module_data

        # Build file-level module for top-level functions
        if functions or class_metadata_list:
            file_module_name = self._get_file_module_name(doc_data.relative_path)

            # Build function entries
            function_entries = []
            for func_data in functions:
                func_entry = self._build_function_entry(
                    func_data,
                    doc_data,
                    symbol_map,
                    call_sites_by_function,
                    global_arity_map,
                )
                function_entries.append(func_entry)

            # Aggregate all calls from function entries for module-level tracking
            module_calls = []
            for func_entry in function_entries:
                module_calls.extend(func_entry.get("dependencies", []))

            file_module = {
                "name": file_module_name,
                "file": doc_data.relative_path,
                "line": 1,
                "functions": function_entries,
                "calls": module_calls,
                "dependencies": self._merge_dependencies_to_dict(doc_data.dependencies),
                "type": "module",
                "module_kind": "module",  # File-level modules are always "module" kind
                "classes": class_metadata_list,  # Track classes defined in this module
                "aliases": doc_data.aliases,
                "imports": [dep.module for dep in doc_data.dependencies],
            }

            # Extract keywords if enabled
            if self.extract_keywords and self.keyword_extractor:
                func_docs = " ".join(f.get("doc", "") for f in function_entries)
                if func_docs.strip():
                    keywords = self._normalize_keywords(
                        self.keyword_extractor.extract_keywords(func_docs)
                    )
                    if keywords:
                        file_module["keywords"] = keywords
                # Also extract keywords for individual functions
                for func_entry in function_entries:
                    func_doc = func_entry.get("doc", "")
                    if func_doc:
                        func_keywords = self._normalize_keywords(
                            self.keyword_extractor.extract_keywords(func_doc)
                        )
                        if func_keywords:
                            func_entry["keywords"] = func_keywords

            modules[file_module_name] = file_module

        return modules

    def _normalize_keywords(self, keywords_result: dict | list) -> dict:
        """
        Normalize keyword extractor output to a simple dict format.

        The keyword extractor may return different formats depending on the extractor type:
        - dict with 'tf_scores' or 'top_keywords' keys
        - list of (keyword, score) tuples
        - simple dict of {keyword: score}

        Args:
            keywords_result: Raw output from keyword extractor

        Returns:
            Dict mapping keyword strings to numeric scores
        """
        if not keywords_result:
            return {}

        # If already a simple dict with numeric values, return as-is
        if isinstance(keywords_result, dict):
            # Check if it's a nested structure from RegularKeywordExtractor
            if "tf_scores" in keywords_result:
                return keywords_result["tf_scores"]
            if "top_keywords" in keywords_result:
                # Convert list of tuples to dict
                return dict(keywords_result["top_keywords"])
            # Assume it's already a simple {keyword: score} dict
            # But verify values are numeric, not nested
            first_value = next(iter(keywords_result.values()), None)
            if isinstance(first_value, (int, float)):
                return keywords_result
            # If values aren't numeric, return empty
            return {}

        # If it's a list of tuples, convert to dict
        if isinstance(keywords_result, list):
            return dict(keywords_result)

        return {}

    def _parse_signature_from_doc(self, doc_text: str) -> tuple[str, str, list[str]]:
        """
        Parse signature and args from SCIP documentation.

        SCIP documentation often contains markdown code blocks with signatures:
        ```python
        def foo(x: int, y: str) -> bool:
        ```

        This extracts the signature, cleans up the doc, and extracts arg names.

        Args:
            doc_text: Raw documentation from SCIP

        Returns:
            Tuple of (signature, clean_doc, args_list)
        """
        signature = ""
        clean_doc = doc_text
        args = []

        # Look for markdown code block with signature
        # Pattern: ```language\n...signature...\n```
        code_block_pattern = r"```(?:python|typescript|javascript|ts|js)?\s*\n(.*?)\n```"
        match = re.search(code_block_pattern, doc_text, re.DOTALL)

        if match:
            signature = match.group(1).strip()
            # Remove the code block from doc
            clean_doc = re.sub(code_block_pattern, "", doc_text, flags=re.DOTALL).strip()

            # Extract args from signature
            args = self._extract_args_from_signature(signature)

        return signature, clean_doc, args

    def _extract_args_from_signature(self, signature: str) -> list[str]:
        """
        Extract argument names from a function signature.

        Args:
            signature: Function signature string (e.g., "def foo(x: int, y: str) -> bool:")

        Returns:
            List of argument names (e.g., ["x", "y"])
        """
        args = []

        # Find parameters between the function's parentheses
        # Need to handle nested parens in type hints like Union[int, float]
        # Find the opening paren after 'def funcname' and match to the closing paren
        first_paren = signature.find("(")
        if first_paren == -1:
            return args

        # Find matching closing paren by counting depth
        depth = 0
        end_idx = -1
        for i in range(first_paren, len(signature)):
            if signature[i] == "(":
                depth += 1
            elif signature[i] == ")":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break

        if end_idx == -1:
            return args

        params_str = signature[first_paren + 1 : end_idx]

        # Split by comma at depth 0 (not inside brackets/parens)
        # This handles type hints like Union[int, float] correctly
        params = []
        current = []
        depth = 0
        for char in params_str:
            if char in "([{":
                depth += 1
                current.append(char)
            elif char in ")]}":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                params.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            params.append("".join(current).strip())

        for param in params:
            if not param or param == "self" or param == "cls":
                continue

            # Handle patterns like:
            # - x: int
            # - y: str = "default"
            # - *args
            # - **kwargs
            # - /  (positional-only marker)

            # Skip positional-only marker
            if param == "/":
                continue

            # Extract just the name (before : or =)
            name_match = re.match(r"^\*{0,2}(\w+)", param)
            if name_match:
                args.append(name_match.group(1))

        return args

    def _build_function_entry(
        self,
        symbol_data: SymbolData,
        doc_data: DocumentData,
        symbol_map: dict,
        call_sites_by_function: dict,
        global_arity_map: dict[str, int] | None = None,
    ) -> dict:
        """
        Build a function entry dict from SymbolData.

        Args:
            symbol_data: Symbol metadata
            doc_data: Document data (for file path)
            symbol_map: SCIP symbol map for documentation
            call_sites_by_function: Pre-grouped call sites
            global_arity_map: Global map of symbol -> arity for cross-file resolution

        Returns:
            Function entry dict
        """
        func_name = self._extract_name(symbol_data.symbol)

        # Get call sites for this function
        call_sites = call_sites_by_function.get(symbol_data.symbol, [])

        # Transform calls to dependencies if enabled
        dependencies = []
        if self.extract_references and call_sites:
            dependencies = self._transform_calls_to_dependencies_fast(
                call_sites,
                doc_data.aliases,
                global_arity_map,
            )

        # Determine visibility type (public/private)
        func_type = "private" if self._is_private(symbol_data.symbol) else "public"

        # Extract signature and args from documentation
        signature = ""
        clean_doc = ""
        args = []

        symbol_info = symbol_map.get(symbol_data.symbol)
        if symbol_info and symbol_info.documentation:
            raw_doc = "\n".join(symbol_info.documentation)
            signature, clean_doc, args = self._parse_signature_from_doc(raw_doc)

        # Compute arity to match args length for schema consistency
        # Priority: use args from docstring if available (excludes self/cls),
        # otherwise fall back to SCIP arity and generate placeholder arg names
        if args:
            # Docstring args are canonical (excludes self/cls)
            arity = len(args)
        elif symbol_data.arity > 0:
            # No docstring args, use SCIP arity and generate placeholders
            arity = symbol_data.arity
            args = [f"arg{i}" for i in range(arity)]
        else:
            # No info from either source
            arity = 0

        func_entry = {
            "name": func_name,
            "arity": arity,
            "line": symbol_data.line,
            "calls": call_sites,
            "dependencies": dependencies,
            "type": func_type,
            "visibility": func_type,  # Same as type for Python (public/private)
            "args": args,
            "signature": signature,
        }

        # Add cleaned documentation if available
        if clean_doc:
            func_entry["doc"] = clean_doc

        return func_entry

    def _format_dependency(self, import_data: ImportData) -> dict:
        """Convert ImportData to dependency dict."""
        return {
            "module": import_data.module,
            "symbols": import_data.symbols,
            "line": import_data.line,
        }

    def _merge_dependencies_to_dict(self, dependencies: list[ImportData]) -> dict:
        """
        Merge dependencies list into Elixir-compatible format.

        Converts a list of ImportData to a dict with 'modules' and 'has_dynamic_calls'.
        This matches the format expected by Cicada's UniversalIndexSchema.

        Args:
            dependencies: List of ImportData objects

        Returns:
            Dict with 'modules' (list of module names) and 'has_dynamic_calls' (bool)
        """
        modules = set()
        has_dynamic_calls = False

        for dep in dependencies:
            modules.add(dep.module)
            # TODO: Detect dynamic calls (e.g., getattr, exec, eval)
            # For now, assume static calls only

        return {
            "modules": sorted(modules),  # Sort for deterministic output
            "has_dynamic_calls": has_dynamic_calls,
        }

    def _build_module_name(self, symbol: str) -> str:
        """
        Build module name for a class.

        For Python, we use the simple class name (not full module path).

        Args:
            symbol: SCIP symbol for the class

        Returns:
            Simple class name
        """
        return self._extract_name(symbol)

    def _get_file_module_name(self, file_path: str) -> str | None:
        """
        Get module name for a file.

        Converts file path to module notation with _file_ prefix, e.g.:
        "cicada/git/history_analyzer.py" -> "_file_cicada.git.history_analyzer"

        This prefix distinguishes file-level modules from class modules
        (e.g., _file_calculator vs Calculator class).

        Args:
            file_path: File path

        Returns:
            Module name with _file_ prefix, or None
        """
        module_name = self._file_path_to_module_name(file_path)
        if module_name:
            return f"_file_{module_name}"
        return None

    def _transform_calls_to_dependencies_fast(
        self,
        call_sites: list[dict],
        aliases: dict[str, str],
        arity_map: dict[str, int] | None = None,
    ) -> list[dict]:
        """
        Transform call sites to dependency format (optimized version).

        This is simplified from the old _transform_calls_to_dependencies
        since we pre-computed arities during extraction.

        Args:
            call_sites: List of call site dicts
            aliases: Import aliases
            arity_map: Global map of symbol -> arity for cross-file resolution

        Returns:
            List of dependency dicts with module, function, arity, and line
        """
        dependencies = []
        seen = set()

        for call_site in call_sites:
            callee_symbol = call_site["callee"]
            line = call_site.get("line", 0)

            # Extract module and function name
            module_name = self._extract_module_from_symbol(callee_symbol)
            func_name = self._extract_name(callee_symbol)

            if not module_name or not func_name:
                continue

            # Resolve aliases
            if module_name in aliases:
                module_name = aliases[module_name]

            # Skip builtins
            if self._is_builtin_module(module_name):
                continue

            # Get arity from global map (supports cross-file resolution)
            # Default to 0 for external functions where we don't have arity info
            arity = 0
            if arity_map and callee_symbol in arity_map:
                arity = arity_map[callee_symbol]

            # Create dependency key (include line to track multiple calls to same function)
            dep_key = (module_name, func_name, arity, line)
            if dep_key in seen:
                continue
            seen.add(dep_key)

            dependencies.append(
                {
                    "module": module_name,
                    "function": func_name,
                    "arity": arity,
                    "line": line,
                }
            )

        return dependencies

    def _get_symbol_type(self, symbol: str) -> str:
        """
        Determine symbol type by parsing SCIP symbol descriptor.

        Delegates to language-specific modules based on the SCIP scheme prefix.

        SCIP symbols have format: scheme language package version descriptor

        Returns:
            One of: 'class', 'method', 'function', 'module', 'parameter',
                   'attribute', 'unknown'
        """
        parts = symbol.split()
        if len(parts) < 5:
            return "unknown"

        scheme = parts[0]
        descriptor = " ".join(parts[4:])

        # Delegate to language-specific symbol type detection
        if scheme.startswith(("scip-typescript", "scip-javascript")):
            return _get_typescript_symbols().get_symbol_type(descriptor)
        else:
            # Default to Python-style parsing (works for Python and unknown languages)
            return _get_python_symbols().get_symbol_type(descriptor)

    def _scip_kind_to_module_kind(self, kind: int) -> str:
        """
        Map SCIP SymbolInformation.Kind to module_kind string.

        SCIP Kind enum values (from scip.proto):
        - Class = 7
        - Interface = 21
        - TypeAlias = 55
        - Type = 54
        - Module = 29
        - Struct = 49
        - Enum = 11
        - Trait = 53
        - UnspecifiedKind = 0

        Returns one of: 'class', 'interface', 'type_alias', 'module', 'struct',
                        'enum', 'trait', 'unknown'
        """
        kind_mapping = {
            7: "class",  # Class
            21: "interface",  # Interface
            55: "type_alias",  # TypeAlias
            54: "type_alias",  # Type (generic type definition)
            29: "module",  # Module
            49: "struct",  # Struct
            11: "enum",  # Enum
            53: "trait",  # Trait
            0: "unknown",  # UnspecifiedKind
        }
        return kind_mapping.get(kind, "unknown")

    def _extract_module_kind_from_moduledoc(self, moduledoc: str) -> str:
        """
        Extract module_kind from moduledoc code fence.

        TypeScript/JavaScript moduledocs have patterns like:
        - ```ts\ninterface StoreApi\n``` -> 'interface'
        - ```ts\ntype SetStateInternal\n``` -> 'type_alias'
        - ```ts\nclass Container\n``` -> 'class'
        - ```ts\nenum Status\n``` -> 'enum'

        This is a fallback when SCIP kind is UnspecifiedKind (0).
        Returns 'unknown' if no pattern matches.
        """
        if not moduledoc:
            return "unknown"

        # Check for TypeScript/JavaScript patterns
        if "```ts\ninterface " in moduledoc or "```typescript\ninterface " in moduledoc:
            return "interface"
        if "```ts\ntype " in moduledoc or "```typescript\ntype " in moduledoc:
            return "type_alias"
        if "```ts\nclass " in moduledoc or "```typescript\nclass " in moduledoc:
            return "class"
        if "```ts\nenum " in moduledoc or "```typescript\nenum " in moduledoc:
            return "enum"

        return "unknown"

    def _extract_name(self, symbol: str) -> str:
        """
        Extract human-readable name from SCIP symbol.

        SCIP symbols look like:
        - scip-python python myproject 1.0 mymodule/MyClass# -> 'MyClass'
        - scip-python python myproject 1.0 mymodule/MyClass#method(). -> 'method'
        - scip-python python myproject 1.0 mymodule/function(). -> 'function'
        - scip-typescript npm pkg 1.0 src/file.ts:Class#method. -> 'method'
        - scip-typescript npm pkg 1.0 src/file.ts:function. -> 'function'

        Returns the appropriate name for each symbol type.
        """
        # Symbol format: scheme language package version descriptors
        # Descriptors are separated by / for hierarchy, # for class members
        parts = symbol.split()
        if len(parts) < 5:
            return symbol  # Fallback

        scheme = parts[0]
        descriptor = " ".join(parts[4:])  # Join remaining parts

        # Remove trailing .
        descriptor = descriptor.rstrip(".")

        # TypeScript/JavaScript: uses / for file path, # for class members, (). for callables
        # Note: TypeScript DOES use (). suffix for functions/methods (similar to Python)
        if scheme.startswith(("scip-typescript", "scip-javascript")):
            # Strip trailing () if present (TypeScript uses (). for callables)
            if descriptor.endswith("()"):
                descriptor = descriptor[:-2]

            # For classes (ends with #): get class name before #
            if descriptor.endswith("#"):
                # e.g., "`file.ts`/Calculator#" -> "Calculator"
                descriptor = descriptor.rstrip("#")
                name = descriptor.split("/")[-1]
            # For methods (contains # with content after): get part after #
            elif "#" in descriptor:
                # e.g., "`file.ts`/Calculator#add" -> "add"
                name = descriptor.split("#")[-1]
            # For module-level functions: get part after /
            elif "/" in descriptor:
                name = descriptor.split("/")[-1]
            else:
                name = descriptor
            return name

        # Python and other languages: use () for callables
        # For classes (ending with #), remove # and get last / component
        if descriptor.endswith("#"):
            descriptor = descriptor.rstrip("#")
            name = descriptor.split("/")[-1]
        # For methods (contains # and ends with ())
        elif "#" in descriptor and descriptor.endswith("()"):
            name = descriptor.split("#")[-1].rstrip("()")
        # For functions and other symbols
        elif "/" in descriptor:
            name = descriptor.split("/")[-1].rstrip("()")
        else:
            name = descriptor.rstrip("()")

        return name

    def _is_private(self, symbol: str) -> bool:
        """
        Determine if a symbol represents a private function/method.

        In Python, names starting with _ are private by convention.
        """
        name = self._extract_name(symbol)
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

    def _get_parent_symbol(self, symbol: str) -> str | None:
        """
        Extract parent symbol from a child symbol.

        For example:
        scip-python python myproject 1.0 mymodule/MyClass#method().
        Returns:
        scip-python python myproject 1.0 mymodule/MyClass#
        """
        if "#" not in symbol:
            return None

        # Remove the last component after #
        parts = symbol.split()
        if len(parts) < 5:
            return None

        descriptor = " ".join(parts[4:])
        if "#" not in descriptor:
            return None

        # Get everything before the last #method part
        descriptor_parts = descriptor.split("#")
        if len(descriptor_parts) < 2:
            return None

        parent_descriptor = "#".join(descriptor_parts[:-1]) + "#"
        parent_symbol = " ".join(parts[:4] + [parent_descriptor])

        return parent_symbol

    def _extract_module_from_symbol(self, symbol: str) -> str | None:
        """
        Extract module name from SCIP symbol.

        Examples:
            "scip-python python pkg 1.0 operations/__init__:" -> "operations"
            "scip-python python pkg 1.0 utils/chain_add()." -> "utils"
            "scip-python python pkg 1.0 typing/List." -> "typing"
            "scip-typescript npm pkg 1.0 `file.ts`/add()." -> "file.ts"

        Args:
            symbol: SCIP symbol string

        Returns:
            Module name, or None if can't be extracted.
            Note: Backticks from TypeScript path wrappers are stripped.
        """
        parts = symbol.split()
        if len(parts) < 5:
            return None

        descriptor = " ".join(parts[4:])

        # Remove trailing markers
        descriptor = descriptor.rstrip(":.#")

        # Handle __init__: case (module import)
        if descriptor.endswith("/__init__"):
            descriptor = descriptor[: -len("/__init__")]

        # Get the module part
        if "/" in descriptor:
            # For "utils/chain_add" -> "utils"
            # For "typing/List" -> "typing"
            # For TypeScript: "`file.ts`/add" -> "file.ts"
            module_path = descriptor.split("/")[0]
            # Strip backticks from TypeScript path wrappers
            module_path = module_path.strip("`")
            return module_path
        elif descriptor:
            # For "operations" (after __init__ removal) -> "operations"
            # Strip backticks from TypeScript path wrappers
            return descriptor.strip("`")

        return None

    def _extract_module_name_from_descriptor(self, symbol: str) -> str:
        """
        Extract fully-qualified module name from SCIP module symbol.

        Converts SCIP descriptor format to Python module naming convention.

        Examples:
            "scip-python python pkg 1.0 calculator/__init__:" -> "calculator"
            "scip-python python pkg 1.0 cicada/mcp/__init__:" -> "cicada.mcp"
            "scip-python python pkg 1.0 cicada/mcp/server/__init__:" -> "cicada.mcp.server"
            "scip-python python pkg 1.0 utils:" -> "utils"
            "scip-python python pkg 1.0 `cicada/mcp/__init__`:" -> "cicada.mcp"
            "scip-python python pkg 1.0 `cicada.mcp.server`/__init__:" -> "cicada.mcp.server"

        Args:
            symbol: SCIP symbol string for a module (must end with :)

        Returns:
            Python module name with dot-separated path components
        """
        parts = symbol.split()
        if len(parts) < 5:
            return ""

        descriptor = " ".join(parts[4:])

        # Remove trailing : for module symbols
        descriptor = descriptor.rstrip(":")

        # Remove backticks if present (SCIP wraps module names in backticks)
        # Format: `module.name` or `module/path`/__init__ or variations
        descriptor = descriptor.replace("`", "")

        # Remove /__init__ suffix if present
        if descriptor.endswith("/__init__"):
            descriptor = descriptor[: -len("/__init__")]

        # Handle .py file extension if present
        if descriptor.endswith(".py"):
            descriptor = descriptor[: -len(".py")]

        # Convert path separators (/) to module separators (.)
        module_name = descriptor.replace("/", ".")

        return module_name

    def _is_builtin_module(self, module_name: str) -> bool:
        """
        Check if a module is a Python builtin or should be excluded.

        Args:
            module_name: Name of the module

        Returns:
            True if module should be excluded from dependencies
        """
        # Python builtins and internal modules to exclude
        excluded = {
            "builtins",
            "__builtins__",
            "__future__",
            "sys",
            "os",  # Can be configurable
            # Add more as needed
        }

        return module_name in excluded

    def _file_path_to_module_name(self, file_path: str) -> str | None:
        """
        Convert file path to Python module name.

        Examples:
            "cicada/git/history_analyzer.py" -> "cicada.git.history_analyzer"
            "calculator.py" -> "calculator"
            "lib/utils/__init__.py" -> "lib.utils"

        Args:
            file_path: File path relative to repository root

        Returns:
            Module name with dot-separated components, or None if invalid
        """
        if not file_path:
            return None

        # Remove .py extension
        if file_path.endswith(".py"):
            file_path = file_path[:-3]

        # Remove __init__ suffix for package modules
        if file_path.endswith("/__init__"):
            file_path = file_path[:-9]

        # Convert path separators to dots
        module_name = file_path.replace("/", ".")

        return module_name if module_name else None

    def _detect_language(self, scip_index: scip_pb2.Index) -> str:
        """
        Detect language from SCIP metadata.

        Args:
            scip_index: SCIP Index

        Returns:
            Language name (e.g., "python", "typescript", "go")
        """
        # Option 1: Check the first document's language field
        if scip_index.documents:
            for doc in scip_index.documents:
                if doc.language:
                    return doc.language

        # Option 2: Parse from tool_info name (e.g., "scip-python" → "python")
        if scip_index.metadata and scip_index.metadata.tool_info:
            tool_name = scip_index.metadata.tool_info.name
            if tool_name:
                # Extract language from tool name
                # Examples: "scip-python" → "python", "scip-typescript" → "typescript"
                if tool_name.startswith("scip-"):
                    return tool_name[5:]  # Remove "scip-" prefix
                return tool_name

        # Fallback to unknown
        return "unknown"

    def _build_metadata(
        self, scip_index: scip_pb2.Index, repo_path: Path, total_modules: int
    ) -> dict:
        """
        Build metadata section of index.

        Args:
            scip_index: SCIP Index
            repo_path: Repository path
            total_modules: Number of modules indexed

        Returns:
            Metadata dict
        """
        # Count total functions across all modules by parsing symbol types
        total_functions = 0
        for doc in scip_index.documents:
            for symbol_info in doc.symbols:
                symbol_type = self._get_symbol_type(symbol_info.symbol)
                if symbol_type in ("function", "method"):
                    total_functions += 1

        metadata: dict[str, Any] = {
            "indexed_at": datetime.now().isoformat(),
            "language": self._detect_language(scip_index),
            "version": "2.0",
            "repo_path": str(repo_path),
            "total_modules": total_modules,
            "total_functions": total_functions,
        }

        # Add SCIP-specific metadata
        if scip_index.metadata:
            metadata["scip_version"] = scip_index.metadata.version
            if scip_index.metadata.tool_info:
                metadata["tool_info"] = {
                    "name": scip_index.metadata.tool_info.name,
                    "version": scip_index.metadata.tool_info.version,
                }

        return metadata

    def _build_reverse_call_index(self, modules: dict) -> dict[str, list[dict]]:
        """
        Build reverse lookup from callee to callers for O(1) "what calls this" queries.

        Iterates through all modules and functions, extracting call sites and inverting
        the relationship: instead of "function X calls [A, B, C]", we build
        "function A is called by [X, Y, Z]".

        Args:
            modules: The fully processed modules dict from convert()

        Returns:
            Dict mapping "ModuleName.functionName" to list of caller info dicts.
            Each caller dict has: module, function, arity, file, line
        """
        reverse_index: dict[str, list[dict]] = {}

        for module_name, module_data in modules.items():
            file_path = module_data.get("file", "")

            for func in module_data.get("functions", []):
                caller_name = func.get("name")
                caller_arity = func.get("arity", 0)

                # Process raw call sites (SCIP format with callee symbol)
                for call in func.get("calls", []):
                    callee_symbol = call.get("callee", "")
                    call_line = call.get("line", 0)

                    if not callee_symbol:
                        continue

                    # Extract function name and module from SCIP symbol
                    callee_name = self._extract_name(callee_symbol)
                    callee_module = self._extract_module_from_symbol(callee_symbol)

                    if not callee_name:
                        continue

                    # Build key: "Module.function" or just "function"
                    key = f"{callee_module}.{callee_name}" if callee_module else callee_name

                    caller_ref = {
                        "module": module_name,
                        "function": caller_name,
                        "arity": caller_arity,
                        "file": file_path,
                        "line": call_line,
                    }

                    if key not in reverse_index:
                        reverse_index[key] = []
                    reverse_index[key].append(caller_ref)

        return reverse_index
