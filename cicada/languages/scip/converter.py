"""Convert SCIP Index to Cicada's UniversalIndexSchema.

This module handles the mapping from SCIP protocol buffer format to
Cicada's JSON index format.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import cicada.languages.scip.scip_pb2 as scip_pb2


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
        Convert SCIP Index to Cicada index format.

        Args:
            scip_index: Parsed SCIP protobuf
            repo_path: Repository root path

        Returns:
            Dict in UniversalIndexSchema format with 'modules' and 'metadata' keys
        """
        modules = {}

        # Build a symbol lookup map for quick access
        symbol_map = self._build_symbol_map(scip_index)

        # Process each document (file)
        for doc in scip_index.documents:
            file_modules = self._convert_document(doc, repo_path, symbol_map)
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

    def _convert_document(self, doc: scip_pb2.Document, repo_path: Path, symbol_map: dict) -> dict:
        """
        Convert a SCIP Document to one or more ModuleData entries.

        For Python:
        - Each class becomes a module
        - Top-level functions are grouped under a pseudo-module named after the file

        Args:
            doc: SCIP Document
            repo_path: Repository root
            symbol_map: Symbol lookup map

        Returns:
            Dict mapping module names to ModuleData dicts
        """
        modules = {}
        file_path = doc.relative_path

        # Extract import aliases from the source file
        # Lazy import to avoid circular dependency
        aliases = {}
        try:
            from cicada.languages.python.alias_extractor import PythonAliasExtractor

            full_path = repo_path / file_path
            alias_extractor = PythonAliasExtractor()
            aliases = alias_extractor.extract_aliases(full_path)
            if self.verbose and aliases:
                print(f"Extracted {len(aliases)} aliases from {file_path}", file=sys.stderr)
        except Exception as e:
            if self.verbose:
                print(f"Warning: Failed to extract aliases from {file_path}: {e}", file=sys.stderr)

        # Extract call sites and dependencies if enabled
        call_sites_by_function = {}
        dependencies = []
        if self.extract_references:
            call_sites_by_function = self._extract_call_sites(doc)
            dependencies = self._extract_dependencies(doc)

        # Separate symbols by type
        classes = []
        module_symbols = []  # Module/package symbols
        functions = []
        methods = {}  # Maps class symbol -> list of methods

        for symbol_info in doc.symbols:
            # Parse symbol descriptor since kind field is not populated by scip-python
            symbol_type = self._get_symbol_type(symbol_info.symbol)

            if symbol_type == "class":
                classes.append(symbol_info)
            elif symbol_type == "module":
                # This is a module/package symbol
                module_symbols.append(symbol_info)
            elif symbol_type == "method":
                # This is a method - find its parent class
                parent_symbol = self._get_parent_symbol(symbol_info.symbol)
                if parent_symbol:
                    methods.setdefault(parent_symbol, []).append(symbol_info)
            elif symbol_type == "function":
                # Top-level function
                functions.append(symbol_info)
            # Skip parameters and other symbol types

        # Track class metadata for module entries
        class_metadata_list = []

        # Convert classes to modules
        for class_info in classes:
            class_name = self._extract_name(class_info.symbol)
            class_methods = methods.get(class_info.symbol, [])
            class_line = self._get_definition_line(class_info.symbol, doc)

            # Count public/private methods
            public_count = sum(1 for m in class_methods if not self._is_private(m.symbol))
            private_count = sum(1 for m in class_methods if self._is_private(m.symbol))

            module_data = {
                "file": file_path,
                "line": class_line,
                "functions": [
                    self._convert_function(method, doc, symbol_map, call_sites_by_function)
                    for method in class_methods
                ],
                "calls": [],  # Module-level calls (not extracted yet)
                "dependencies": dependencies,
            }

            # Add documentation if available
            class_doc = None
            if class_info.documentation:
                moduledoc = "\n".join(class_info.documentation)
                module_data["moduledoc"] = moduledoc
                class_doc = moduledoc

                # Extract keywords from module documentation
                if self.extract_keywords and self.keyword_extractor:
                    try:
                        # Combine class name and documentation for keyword extraction
                        module_text = f"{class_name} {moduledoc}"
                        results = self.keyword_extractor.extract_keywords(module_text, top_n=10)
                        # Convert list of tuples to dict
                        module_keywords: dict[str, float] = dict(results["top_keywords"])
                        if module_keywords:
                            module_data["keywords"] = module_keywords  # type: ignore[typeddict-item]
                    except Exception as e:
                        if self.verbose:
                            print(
                                f"Warning: Module keyword extraction failed for {class_name}: {e}",
                                file=sys.stderr,
                            )

            # Add function counts
            module_data["total_functions"] = len(class_methods)
            module_data["public_functions"] = public_count
            module_data["private_functions"] = private_count

            # Add parent module reference (file path without .py extension, converted to module name)
            # e.g., "cicada/git/history_analyzer.py" -> "cicada.git.history_analyzer"
            parent_module = self._file_path_to_module_name(file_path)
            if parent_module:
                module_data["parent_module"] = parent_module

            modules[class_name] = module_data

            # Collect class metadata for module entries
            class_metadata_list.append(
                {
                    "name": class_name,
                    "line": class_line,
                    "doc": class_doc,
                    "public_methods": public_count,
                    "private_methods": private_count,
                    "total_methods": len(class_methods),
                }
            )

        # Convert module symbols to module entries
        for module_info in module_symbols:
            module_name = self._extract_module_name_from_descriptor(module_info.symbol)

            # Only create module if we got a valid name
            if not module_name:
                continue

            # Skip if this module is already in our modules dict (shouldn't happen)
            if module_name in modules:
                continue

            # Module entries represent packages/namespaces, not collections of functions
            # Functions belong to classes or are captured in _file_ entries
            # This is just metadata about the module itself
            module_data = {
                "file": file_path,
                "line": self._get_definition_line(module_info.symbol, doc),
                "functions": [],  # Module entries don't contain functions directly
                "calls": [],  # Module-level calls (not extracted yet)
                "dependencies": dependencies,
                "total_functions": 0,
                "public_functions": 0,
                "private_functions": 0,
                "classes": class_metadata_list,  # Classes defined in this module
            }

            # Add documentation if available
            if module_info.documentation:
                moduledoc = "\n".join(module_info.documentation)
                module_data["moduledoc"] = moduledoc

                # Extract keywords from module documentation
                if self.extract_keywords and self.keyword_extractor:
                    try:
                        # Combine module name and documentation for keyword extraction
                        module_text = f"{module_name} {moduledoc}"
                        results = self.keyword_extractor.extract_keywords(module_text, top_n=10)
                        # Convert list of tuples to dict
                        module_keywords: dict[str, float] = dict(results["top_keywords"])
                        if module_keywords:
                            module_data["keywords"] = module_keywords  # type: ignore[typeddict-item]
                    except Exception as e:
                        if self.verbose:
                            print(
                                f"Warning: Module keyword extraction failed for {module_name}: {e}",
                                file=sys.stderr,
                            )

            modules[module_name] = module_data

        # If there are top-level functions, create a pseudo-module for the file
        if functions:
            file_stem = Path(file_path).stem
            module_name = f"_file_{file_stem}"

            module_data = {
                "file": file_path,
                "line": 1,
                "functions": [
                    self._convert_function(func, doc, symbol_map, call_sites_by_function)
                    for func in functions
                ],
                "calls": [],  # Module-level calls (not extracted yet)
                "dependencies": dependencies,
                "total_functions": len(functions),
                "public_functions": sum(1 for f in functions if not self._is_private(f.symbol)),
                "private_functions": sum(1 for f in functions if self._is_private(f.symbol)),
            }

            modules[module_name] = module_data

        # Aggregate call dependencies from all functions and merge with import dependencies
        if self.extract_references:
            # Get modules from import dependencies
            import_modules = {dep["module"] for dep in dependencies if "module" in dep}

            # Get modules from function call dependencies
            call_modules = self._aggregate_call_dependencies(modules)

            # Merge both sources
            all_modules = import_modules | call_modules

            # Update all modules with standardized dependency format
            # Match Elixir indexer's format: {"modules": [...], "has_dynamic_calls": bool}
            for module_data in modules.values():
                module_data["dependencies"] = {
                    "modules": sorted(all_modules),
                    "has_dynamic_calls": False,
                }

                # Add Elixir-compatible import/alias fields for MCP tool compatibility
                # This allows Python modules to work with existing MCP handlers
                # that were designed for Elixir
                module_data["imports"] = sorted(all_modules)
                module_data["aliases"] = aliases  # Extracted from "import X as Y" patterns
                module_data["requires"] = []  # Elixir-specific, not applicable to Python
                module_data["uses"] = []  # Elixir-specific, not applicable to Python
        else:
            # Even when not extracting references, add empty Elixir-compatible fields
            # for consistency and MCP tool compatibility
            for module_data in modules.values():
                module_data["dependencies"] = {
                    "modules": [],
                    "has_dynamic_calls": False,
                }
                module_data["imports"] = []
                module_data["aliases"] = aliases  # Still extract aliases even without call sites
                module_data["requires"] = []
                module_data["uses"] = []

        return modules

    def _parse_signature_and_doc(self, documentation: list[str]) -> tuple[str, str]:
        """
        Parse SCIP documentation to extract signature and docstring separately.

        SCIP stores documentation as markdown with format:
        ```language
        function signature here
        ```

        Actual docstring text here.

        Args:
            documentation: List of documentation strings

        Returns:
            Tuple of (signature, docstring)
        """
        if not documentation:
            return "", ""

        full_doc = "\n".join(documentation)

        # Extract code block (signature) using regex
        # Pattern: ```language\n...signature...\n```
        code_block_match = re.match(r"```[a-zA-Z]*\n(.*?)\n```\s*(.*)", full_doc, re.DOTALL)

        if code_block_match:
            signature = code_block_match.group(1).strip()
            docstring = code_block_match.group(2).strip()
            return signature, docstring

        # If no code block found, treat entire text as docstring
        return "", full_doc.strip()

    def _convert_function(
        self,
        symbol_info: scip_pb2.SymbolInformation,
        doc,
        symbol_map: dict,
        call_sites: dict[str, list[dict]] | None = None,
    ) -> dict[str, Any]:
        """
        Convert SymbolInformation to FunctionData dict.

        Args:
            symbol_info: SCIP SymbolInformation for function/method
            doc: Parent document
            symbol_map: Symbol lookup map for finding parameters
            call_sites: Dict mapping function symbol to list of call sites

        Returns:
            FunctionData dict
        """
        name = self._extract_name(symbol_info.symbol)
        is_private = self._is_private(symbol_info.symbol)
        args = self._extract_args(symbol_info.symbol, doc)

        # Parse signature and docstring from documentation
        signature, docstring = self._parse_signature_and_doc(list(symbol_info.documentation))

        func_data: dict[str, Any] = {
            "name": name,
            "arity": len(args),
            "args": args,
            "type": "private" if is_private else "public",
            "line": self._get_definition_line(symbol_info.symbol, doc),
        }

        # Add call sites if available
        if call_sites and symbol_info.symbol in call_sites:
            func_data["calls"] = call_sites[symbol_info.symbol]
            # Transform call sites to dependency format for MCP handlers
            func_data["dependencies"] = self._transform_calls_to_dependencies(
                call_sites[symbol_info.symbol], symbol_map
            )
        else:
            func_data["calls"] = []
            func_data["dependencies"] = []

        # Add signature if extracted
        if signature:
            func_data["signature"] = signature

        # Add docstring if available
        if docstring:
            func_data["doc"] = docstring

            # Extract keywords from function name and docstring
            if self.extract_keywords and self.keyword_extractor:
                try:
                    # Combine function name and documentation for keyword extraction
                    func_text = f"{name} {docstring}"
                    results = self.keyword_extractor.extract_keywords(func_text, top_n=10)
                    # Convert list of tuples to dict
                    func_keywords: dict[str, float] = dict(results["top_keywords"])
                    if func_keywords:
                        func_data["keywords"] = func_keywords  # type: ignore[typeddict-item]
                except Exception as e:
                    if self.verbose:
                        print(
                            f"Warning: Function keyword extraction failed for {name}: {e}",
                            file=sys.stderr,
                        )

        return func_data

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

    def _extract_args(self, function_symbol: str, doc: scip_pb2.Document) -> list[str]:
        """
        Extract function arguments from SCIP document.

        SCIP represents parameters as separate symbols:
        - Function: scip-python python pkg 1.0 module/Class#method().
        - Param 1:  scip-python python pkg 1.0 module/Class#method().(param1)
        - Param 2:  scip-python python pkg 1.0 module/Class#method().(param2)

        Args:
            function_symbol: The function's SCIP symbol
            doc: SCIP Document containing all symbols

        Returns:
            List of parameter names in order
        """
        # Remove trailing dot from function symbol
        function_prefix = function_symbol.rstrip(".")

        # Find all parameter symbols for this function
        params = []
        for symbol_info in doc.symbols:
            symbol = symbol_info.symbol
            symbol_type = self._get_symbol_type(symbol)

            if symbol_type == "parameter" and symbol.startswith(function_prefix + ".("):
                # Check if this parameter belongs to our function
                # Parameter format: function_symbol(param_name)
                # Extract parameter name from .(param_name)
                param_part = symbol[len(function_prefix) :]  # Gets ".(param_name)"
                if param_part.startswith(".(") and param_part.endswith(")"):
                    param_name = param_part[2:-1]  # Remove ".(" and ")"
                    params.append(param_name)

        return params

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

    def _get_definition_line(self, symbol: str, doc: scip_pb2.Document) -> int:
        """
        Find the line number where a symbol is defined.

        Searches through document occurrences for the definition.
        SCIP uses 0-indexed line numbers, so we add 1 to convert to 1-indexed.
        """
        for occurrence in doc.occurrences:
            # Check if this is the symbol and it's a definition (symbol_roles is a bitfield)
            if occurrence.symbol == symbol and (
                occurrence.symbol_roles & scip_pb2.SymbolRole.Definition
            ):
                # Convert from 0-indexed to 1-indexed line numbers
                return (occurrence.range[0] + 1) if occurrence.range else 1

        return 1  # Fallback to line 1

    def _find_enclosing_function(self, doc: scip_pb2.Document, line: int) -> str | None:
        """
        Find which function/method contains the given line number.

        Args:
            doc: SCIP Document
            line: Line number to check

        Returns:
            Symbol of the enclosing function, or None if not in a function
        """
        # Build a list of function definitions with their ranges
        function_ranges = []

        for occurrence in doc.occurrences:
            # Only look at definitions
            if not (occurrence.symbol_roles & scip_pb2.SymbolRole.Definition):
                continue

            # Check if this is a function or method
            symbol_type = self._get_symbol_type(occurrence.symbol)
            if symbol_type not in ("function", "method"):
                continue

            # Get the function's range (convert from 0-indexed to 1-indexed)
            # enclosing_range format: [start_line, start_col, end_line, end_col]
            if occurrence.enclosing_range and len(occurrence.enclosing_range) >= 3:
                start_line = occurrence.enclosing_range[0] + 1
                end_line = occurrence.enclosing_range[2] + 1  # Use index 2, not 1!
                function_ranges.append((start_line, end_line, occurrence.symbol))
            elif occurrence.range:
                # If no enclosing_range, use the definition line as a start point
                # This is less accurate but better than nothing
                start_line = occurrence.range[0] + 1
                # Assume function ends at end of file (we'll refine this later)
                function_ranges.append((start_line, float("inf"), occurrence.symbol))

        # Find the most specific (smallest) function that contains this line
        best_match = None
        best_range_size = float("inf")

        for start, end, symbol in function_ranges:
            if start <= line <= end:
                range_size = end - start
                if range_size < best_range_size:
                    best_match = symbol
                    best_range_size = range_size

        return best_match

    def _extract_call_sites(self, doc: scip_pb2.Document) -> dict[str, list[dict]]:
        """
        Extract call sites from SCIP occurrences.

        Parses SCIP occurrences with ReadAccess role to find where functions are called.
        Maps each call back to the function that contains it.

        Args:
            doc: SCIP Document

        Returns:
            Dict mapping function symbol → list of call site dicts.
            Each call site dict contains:
                - callee: Symbol being called
                - file: File containing the call
                - line: Line number of the call
        """
        call_sites = {}

        for occurrence in doc.occurrences:
            # Filter for ReadAccess (0x8) - indicates usage/call
            # Skip definitions (0x1) and other roles
            if not (occurrence.symbol_roles & scip_pb2.SymbolRole.ReadAccess):
                continue

            # Skip if this is also a definition (e.g., function parameter definitions)
            if occurrence.symbol_roles & scip_pb2.SymbolRole.Definition:
                continue

            # Only include function/method calls (symbols ending with "().")
            # This filters out type references (ending with "#"), parameters (ending with ")"),
            # and module imports (ending with ":")
            if not occurrence.symbol.endswith("()."):
                continue

            # Get call location
            callee_symbol = occurrence.symbol
            # Convert from 0-indexed to 1-indexed line numbers
            call_line = (occurrence.range[0] + 1) if occurrence.range else 0

            if call_line == 0:
                continue  # Skip invalid line numbers

            # Find which function contains this call
            caller_symbol = self._find_enclosing_function(doc, call_line)

            if not caller_symbol:
                # Call is at module level (not inside a function)
                # Skip for now - could track module-level calls in future
                continue

            # Create call site record
            call_site = {
                "callee": callee_symbol,
                "file": doc.relative_path,
                "line": call_line,
            }

            # Add to the caller's call list
            call_sites.setdefault(caller_symbol, []).append(call_site)

        return call_sites

    def _extract_dependencies(self, doc: scip_pb2.Document) -> list[dict]:
        """
        Extract module dependencies (imports) from SCIP occurrences.

        In SCIP, import statements are represented as ReadAccess occurrences
        at the top of the file. We identify them by:
        1. ReadAccess role (indicates usage/reference)
        2. Early line numbers (typically lines 1-20 for imports)
        3. Module symbols (ending with ":") or imported function/class symbols

        Args:
            doc: SCIP Document

        Returns:
            List of dependency dicts, each containing:
                - module: Name of the imported module
                - symbols: List of imported symbols (if any)
                - line: Line number of the import statement
        """
        dependencies = []
        seen_imports = set()  # Track what we've already added

        # Group occurrences by line number to handle multi-symbol imports
        imports_by_line = {}

        for occurrence in doc.occurrences:
            # Filter for ReadAccess (0x8) - indicates usage/reference
            if not (occurrence.symbol_roles & scip_pb2.SymbolRole.ReadAccess):
                continue

            # Skip if this is a definition (e.g., local variable definitions)
            if occurrence.symbol_roles & scip_pb2.SymbolRole.Definition:
                continue

            # Get line number (convert from 0-indexed to 1-indexed)
            line = (occurrence.range[0] + 1) if occurrence.range else 0
            if line == 0:
                continue

            # Focus on early lines where imports typically occur
            # This helps distinguish imports from regular function calls
            # Configurable limit (default 50) to handle files with large headers/docstrings
            if line > self.import_search_lines:
                break  # SCIP occurrences are sorted by line number

            symbol = occurrence.symbol

            # Extract module name from symbol
            # SCIP symbols look like: "scip-python python pkg version module/path:""
            # or "scip-python python pkg version module/function()."
            module_name = self._extract_module_from_symbol(symbol)

            # Skip builtins and standard library internals
            if module_name and not self._is_builtin_module(module_name):
                # Check if this is a module import (ends with ":")
                is_module_import = symbol.endswith(":")

                if is_module_import:
                    # This is a module-level import: "import foo" or "from foo import ..."
                    if module_name not in seen_imports:
                        dependencies.append(
                            {
                                "module": module_name,
                                "symbols": [],
                                "line": line,
                            }
                        )
                        seen_imports.add(module_name)
                else:
                    # This is a symbol import: "from foo import bar"
                    # Group by line number to collect all symbols from same import
                    if line not in imports_by_line:
                        imports_by_line[line] = {
                            "module": module_name,
                            "symbols": [],
                            "line": line,
                        }

                    # Extract symbol name
                    symbol_name = self._extract_name(symbol)
                    if symbol_name and symbol_name not in imports_by_line[line]["symbols"]:
                        imports_by_line[line]["symbols"].append(symbol_name)

        # Add symbol imports to dependencies
        for _line, import_data in imports_by_line.items():
            module_name = import_data["module"]
            # Only add if we have symbols and module not already added as bare import
            if import_data["symbols"] and module_name not in seen_imports:
                dependencies.append(import_data)
                seen_imports.add(module_name)

        return dependencies

    def _transform_calls_to_dependencies(
        self, call_sites: list[dict], symbol_map: dict
    ) -> list[dict]:
        """
        Transform SCIP call sites into Cicada dependency format.

        Converts call site format from:
            {"callee": "scip-python...", "file": "path", "line": 42}
        To dependency format:
            {"module": "operations", "function": "add", "arity": 2, "line": 42}

        Args:
            call_sites: List of call site dicts with callee, file, and line
            symbol_map: Symbol -> SymbolInformation lookup for arity extraction

        Returns:
            List of dependency dicts in Cicada format
        """
        dependencies = []

        for call in call_sites:
            callee_symbol = call["callee"]

            # Extract module name from SCIP symbol
            module_name = self._extract_module_from_symbol(callee_symbol)

            # Extract function name from SCIP symbol
            function_name = self._extract_name(callee_symbol)

            # Get arity from symbol information
            arity = self._get_function_arity(callee_symbol, symbol_map)

            # Build dependency record
            # Note: module_name can be None for local calls within same module
            dependency = {
                "module": module_name,
                "function": function_name,
                "arity": arity,
                "line": call["line"],
            }

            dependencies.append(dependency)

        return dependencies

    def _get_function_arity(self, function_symbol: str, symbol_map: dict) -> int:
        """
        Get function arity from SCIP symbol information.

        Args:
            function_symbol: SCIP symbol for the function
            symbol_map: Symbol -> SymbolInformation lookup

        Returns:
            Function arity (number of parameters), or 0 if unknown
        """
        # Look up symbol information
        symbol_info = symbol_map.get(function_symbol)

        if not symbol_info:
            # Symbol not in our index (e.g., external library, builtin)
            return 0

        # Count parameters by looking for parameter symbols in the index
        # Parameter symbols have format: "function_symbol(param_name)"
        # We need to scan the symbol_map for all parameters of this function
        function_prefix = function_symbol.rstrip(".")
        param_count = 0

        for sym in symbol_map:
            symbol_type = self._get_symbol_type(sym)
            if symbol_type == "parameter" and sym.startswith(function_prefix + ".("):
                param_count += 1

        return param_count

    def _aggregate_call_dependencies(self, modules: dict) -> set[str]:
        """
        Aggregate unique module dependencies from all function calls.

        Scans all functions in all modules and collects unique module names
        from their dependencies.

        Args:
            modules: Dict mapping module names to ModuleData dicts

        Returns:
            Set of unique module names that are dependencies
        """
        unique_modules = set()

        for module_data in modules.values():
            for func in module_data["functions"]:
                if "dependencies" in func:
                    for dep in func["dependencies"]:
                        module_name = dep.get("module")
                        # Only add non-None module names (skip local calls)
                        if module_name:
                            unique_modules.add(module_name)

        return unique_modules

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
