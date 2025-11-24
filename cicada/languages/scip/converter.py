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

        # TWO-PHASE PROCESSING
        for doc in scip_index.documents:
            # Phase 1: Extract all SCIP data in single pass (no nested loops!)
            doc_data = self._extract_document_data(doc, repo_path)

            # Phase 2: Process intermediate data to build modules
            file_modules = self._process_document_data(doc_data, symbol_map)

            modules.update(file_modules)

        # Build metadata
        metadata = self._build_metadata(scip_index, repo_path, len(modules))

        return {"modules": modules, "metadata": metadata}

    def _build_symbol_map(self, scip_index: scip_pb2.Index) -> dict:
        """Build a map of symbol -> SymbolInformation for quick lookup."""
        symbol_map = {}
        for doc in scip_index.documents:
            for symbol_info in doc.symbols:
                symbol_map[symbol_info.symbol] = symbol_info
        return symbol_map

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
        aliases = {}
        try:
            from cicada.languages.python.alias_extractor import PythonAliasExtractor

            full_path = repo_path / doc.relative_path
            alias_extractor = PythonAliasExtractor()
            aliases = alias_extractor.extract_aliases(full_path)
            if self.verbose and aliases:
                print(f"Extracted {len(aliases)} aliases from {doc.relative_path}", file=sys.stderr)
        except Exception as e:
            if self.verbose:
                print(
                    f"Warning: Failed to extract aliases from {doc.relative_path}: {e}",
                    file=sys.stderr,
                )

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

            # === Handle DEFINITIONS ===
            if is_definition:
                # Extract documentation
                doc_text = ""
                if occurrence.symbol_roles & scip_pb2.SymbolRole.Test:
                    doc_text = ""  # Skip test documentation for now

                # Store symbol metadata
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
                            # Fallback: use definition line as start with reasonable upper bound
                            # Use 10000 as a practical file length limit
                            start_line = occurrence.range[0] + 1
                            function_ranges.append((start_line, 10000, symbol))

                    # Count parameters: increment parent function's param count
                    if symbol_type == "parameter":
                        # Extract parent function symbol from parameter symbol
                        # Parameter format: "function_symbol.(param_name)"
                        parent_func = self._extract_function_from_parameter(symbol)
                        if parent_func:
                            param_counts[parent_func] = param_counts.get(parent_func, 0) + 1

            # === Handle CALL SITES (ReadAccess, not Definition) ===
            if is_read_access and not is_definition:
                # Function/method calls: symbols ending with "()."
                # Only collect if extract_references is enabled
                if self.extract_references and symbol.endswith("()."):
                    call_sites.append(
                        CallSite(
                            callee_symbol=symbol,
                            line=line,
                            caller_symbol=None,  # Will be set later via binary search
                        )
                    )

                # Import statements: early lines (<= import_search_lines)
                if line <= self.import_search_lines:
                    module_name = self._extract_module_from_symbol(symbol)

                    if module_name and not self._is_builtin_module(module_name):
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

                            # Extract symbol name
                            symbol_name = self._extract_name(symbol)
                            if symbol_name and symbol_name not in imports_by_line[line].symbols:
                                imports_by_line[line].symbols.append(symbol_name)

        # Consolidate imports from imports_by_line
        dependencies.extend(imports_by_line.values())

        # Update function arities from param_counts
        for func_symbol, count in param_counts.items():
            if func_symbol in symbols:
                symbols[func_symbol].arity = count

        # Sort function ranges by start line for binary search
        function_ranges.sort(key=lambda x: x[0])

        # Match call sites to enclosing functions using FAST binary search
        # Only if extract_references is enabled
        if self.extract_references:
            for call in call_sites:
                call.caller_symbol = self._find_enclosing_fast(call.line, function_ranges)

        return DocumentData(
            relative_path=doc.relative_path,
            aliases=aliases,
            symbols=symbols,
            function_ranges=function_ranges,
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
        func_symbol = parameter_symbol[:idx]
        if not func_symbol.endswith("()."):
            func_symbol += "()."

        return func_symbol

    def _find_enclosing_fast(
        self, line: int, function_ranges: list[tuple[int, int, str]]
    ) -> str | None:
        """
        Find enclosing function using binary search on pre-sorted ranges.

        This replaces the O(n) linear search in _find_enclosing_function()
        with O(log n) binary search on the start lines, then checks nearby
        candidates for the smallest enclosing range.

        Args:
            line: Line number to check
            function_ranges: Sorted list of (start_line, end_line, symbol) tuples

        Returns:
            Symbol of enclosing function, or None if not in a function
        """
        import bisect

        if not function_ranges:
            return None

        # Binary search for the rightmost function that starts at or before line
        start_lines = [start for start, _, _ in function_ranges]
        idx = bisect.bisect_right(start_lines, line) - 1

        # If line is before all functions, no enclosing function exists
        if idx < 0:
            return None

        # Check candidates starting from idx (functions that might contain this line)
        best_match = None
        best_range_size = float("inf")

        # Only check functions whose start_line <= line
        for i in range(idx, len(function_ranges)):
            start, end, symbol = function_ranges[i]

            # If this function starts after line, no more candidates
            if start > line:
                break

            # Check if line is within this function's range
            if start <= line <= end:
                range_size = end - start
                if range_size < best_range_size:
                    best_match = symbol
                    best_range_size = range_size

        return best_match

    def _process_document_data(self, doc_data: DocumentData, symbol_map: dict) -> dict:
        """
        Phase 2: Process intermediate data to build Cicada modules.

        This method operates on the pre-extracted DocumentData and doesn't
        access SCIP occurrences, making it much faster (simple dict operations).

        Args:
            doc_data: Pre-extracted document data from Phase 1
            symbol_map: Symbol lookup map for documentation

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
                )
                function_entries.append(func_entry)

            # Create class module
            module_data = {
                "file": doc_data.relative_path,
                "line": class_data.line,
                "functions": function_entries,
                "calls": [],
                "dependencies": [self._format_dependency(dep) for dep in doc_data.dependencies],
            }

            # Add documentation
            symbol_info = symbol_map.get(class_data.symbol)
            if symbol_info and symbol_info.documentation:
                module_data["moduledoc"] = "\n".join(symbol_info.documentation)

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
                )
                function_entries.append(func_entry)

            file_module = {
                "name": file_module_name,
                "file": doc_data.relative_path,
                "line": 1,
                "functions": function_entries,
                "calls": [],
                "dependencies": [self._format_dependency(dep) for dep in doc_data.dependencies],
                "type": "module",
                "classes": class_metadata_list,  # Track classes defined in this module
            }

            modules[file_module_name] = file_module

        return modules

    def _build_function_entry(
        self,
        symbol_data: SymbolData,
        doc_data: DocumentData,
        symbol_map: dict,
        call_sites_by_function: dict,
    ) -> dict:
        """
        Build a function entry dict from SymbolData.

        Args:
            symbol_data: Symbol metadata
            doc_data: Document data (for file path)
            symbol_map: SCIP symbol map for documentation
            call_sites_by_function: Pre-grouped call sites

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
            )

        func_entry = {
            "name": func_name,
            "arity": symbol_data.arity,
            "line": symbol_data.line,
            "calls": call_sites,
            "dependencies": dependencies,
        }

        # Add documentation
        symbol_info = symbol_map.get(symbol_data.symbol)
        if symbol_info and symbol_info.documentation:
            func_entry["doc"] = "\n".join(symbol_info.documentation)

        return func_entry

    def _format_dependency(self, import_data: ImportData) -> dict:
        """Convert ImportData to dependency dict."""
        return {
            "module": import_data.module,
            "symbols": import_data.symbols,
            "line": import_data.line,
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

        Converts file path to module notation, e.g.:
        "cicada/git/history_analyzer.py" -> "cicada.git.history_analyzer"

        Args:
            file_path: File path

        Returns:
            Module name or None
        """
        return self._file_path_to_module_name(file_path)

    def _transform_calls_to_dependencies_fast(
        self,
        call_sites: list[dict],
        aliases: dict[str, str],
    ) -> list[dict]:
        """
        Transform call sites to dependency format (optimized version).

        This is simplified from the old _transform_calls_to_dependencies
        since we pre-computed arities during extraction.

        Args:
            call_sites: List of call site dicts
            aliases: Import aliases

        Returns:
            List of dependency dicts
        """
        dependencies = []
        seen = set()

        for call_site in call_sites:
            callee_symbol = call_site["callee"]

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

            # Get arity (default 0 for external functions)
            arity = 0

            # Create dependency key
            dep_key = (module_name, func_name, arity)
            if dep_key in seen:
                continue
            seen.add(dep_key)

            dependencies.append(
                {
                    "module": module_name,
                    "name": func_name,
                    "arity": arity,
                }
            )

        return dependencies

    def _get_symbol_type(self, symbol: str) -> str:
        """
        Determine symbol type by parsing SCIP symbol descriptor.

        SCIP symbols have format: scheme language package version descriptor
        Examples:
        - scip-python python sample_python 0.1.0 calculator/__init__: -> module
        - scip-python python sample_python 0.1.0 calculator/Calculator# -> class
        - scip-python python sample_python 0.1.0 calculator/Calculator#add(). -> method
        - scip-python python sample_python 0.1.0 calculator/helper_function(). -> function
        - scip-python python sample_python 0.1.0 calculator/Calculator#add().(x) -> parameter

        Returns:
            One of: 'class', 'method', 'function', 'module', 'parameter', 'unknown'
        """
        parts = symbol.split()
        if len(parts) < 5:
            return "unknown"

        descriptor = " ".join(parts[4:])

        # Parameter: ends with .(param_name)
        if re.match(r".*\.\([^)]+\)$", descriptor):
            return "parameter"

        # Module/namespace: ends with :
        if descriptor.endswith(":"):
            return "module"

        # Class: ends with # (no method following)
        if descriptor.endswith("#"):
            return "class"

        # Method: contains # and ends with ().
        if "#" in descriptor and descriptor.endswith("()."):
            return "method"

        # Function: no # but ends with ().
        if "#" not in descriptor and descriptor.endswith("()."):
            return "function"

        # Attribute/variable: ends with . (but not ().)
        if descriptor.endswith(".") and not descriptor.endswith("()."):
            return "attribute"

        return "unknown"

    def _extract_name(self, symbol: str) -> str:
        """
        Extract human-readable name from SCIP symbol.

        SCIP symbols look like:
        - scip-python python myproject 1.0 mymodule/MyClass# -> 'MyClass'
        - scip-python python myproject 1.0 mymodule/MyClass#method(). -> 'method'
        - scip-python python myproject 1.0 mymodule/function(). -> 'function'

        Returns the appropriate name for each symbol type.
        """
        # Symbol format: scheme language package version descriptors
        # Descriptors are separated by / for hierarchy, # for class members
        parts = symbol.split()
        if len(parts) < 5:
            return symbol  # Fallback

        descriptor = " ".join(parts[4:])  # Join remaining parts

        # Remove trailing . and ()
        descriptor = descriptor.rstrip(".")

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

        Args:
            symbol: SCIP symbol string

        Returns:
            Module name, or None if can't be extracted
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
            module_path = descriptor.split("/")[0]
            return module_path
        elif descriptor:
            # For "operations" (after __init__ removal) -> "operations"
            return descriptor

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
