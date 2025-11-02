"""Convert SCIP Index to Cicada's UniversalIndexSchema.

This module handles the mapping from SCIP protocol buffer format to
Cicada's JSON index format.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from cicada.languages.scip import scip_pb2


class SCIPConverter:
    """Convert SCIP Index to Cicada's UniversalIndexSchema."""

    def __init__(
        self, extract_keywords: bool = False, keyword_extractor=None, verbose: bool = False
    ):
        """
        Initialize SCIP converter.

        Args:
            extract_keywords: If True, extract keywords from documentation
            keyword_extractor: Keyword extractor instance (LightweightKeywordExtractor or KeyBERTExtractor)
            verbose: If True, print progress messages
        """
        self.extract_keywords = extract_keywords
        self.keyword_extractor = keyword_extractor
        self.verbose = verbose

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

        # Separate symbols by type
        classes = []
        functions = []
        methods = {}  # Maps class symbol -> list of methods

        for symbol_info in doc.symbols:
            # Parse symbol descriptor since kind field is not populated by scip-python
            symbol_type = self._get_symbol_type(symbol_info.symbol)

            if symbol_type == "class":
                classes.append(symbol_info)
            elif symbol_type == "method":
                # This is a method - find its parent class
                parent_symbol = self._get_parent_symbol(symbol_info.symbol)
                if parent_symbol:
                    methods.setdefault(parent_symbol, []).append(symbol_info)
            elif symbol_type == "function":
                # Top-level function
                functions.append(symbol_info)
            # Skip parameters, modules, and other symbol types

        # Convert classes to modules
        for class_info in classes:
            class_name = self._extract_name(class_info.symbol)
            class_methods = methods.get(class_info.symbol, [])

            module_data = {
                "file": file_path,
                "line": self._get_definition_line(class_info.symbol, doc),
                "functions": [
                    self._convert_function(method, doc, symbol_map) for method in class_methods
                ],
                "calls": [],  # MVP: Skip call extraction
                "dependencies": [],  # MVP: Skip dependency extraction
            }

            # Add documentation if available
            if class_info.documentation:
                moduledoc = "\n".join(class_info.documentation)
                module_data["moduledoc"] = moduledoc

                # Extract keywords from module documentation
                if self.extract_keywords and self.keyword_extractor:
                    try:
                        # Combine class name and documentation for keyword extraction
                        module_text = f"{class_name} {moduledoc}"
                        module_keywords = self.keyword_extractor.extract_keywords_simple(
                            module_text, top_n=10
                        )
                        if module_keywords:
                            module_data["keywords"] = module_keywords
                    except Exception as e:
                        if self.verbose:
                            print(
                                f"Warning: Module keyword extraction failed for {class_name}: {e}",
                                file=sys.stderr,
                            )

            # Add function counts
            module_data["total_functions"] = len(class_methods)
            module_data["public_functions"] = sum(
                1 for m in class_methods if not self._is_private(m.symbol)
            )
            module_data["private_functions"] = sum(
                1 for m in class_methods if self._is_private(m.symbol)
            )

            modules[class_name] = module_data

        # If there are top-level functions, create a pseudo-module for the file
        if functions:
            file_stem = Path(file_path).stem
            module_name = f"_file_{file_stem}"

            module_data = {
                "file": file_path,
                "line": 1,
                "functions": [self._convert_function(func, doc, symbol_map) for func in functions],
                "calls": [],
                "dependencies": [],
                "total_functions": len(functions),
                "public_functions": sum(1 for f in functions if not self._is_private(f.symbol)),
                "private_functions": sum(1 for f in functions if self._is_private(f.symbol)),
            }

            modules[module_name] = module_data

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
        self, symbol_info: scip_pb2.SymbolInformation, doc, symbol_map: dict
    ) -> dict:
        """
        Convert SymbolInformation to FunctionData dict.

        Args:
            symbol_info: SCIP SymbolInformation for function/method
            doc: Parent document
            symbol_map: Symbol lookup map for finding parameters

        Returns:
            FunctionData dict
        """
        name = self._extract_name(symbol_info.symbol)
        is_private = self._is_private(symbol_info.symbol)
        args = self._extract_args(symbol_info.symbol, doc)

        # Parse signature and docstring from documentation
        signature, docstring = self._parse_signature_and_doc(list(symbol_info.documentation))

        func_data = {
            "name": name,
            "arity": len(args),
            "args": args,
            "type": "private" if is_private else "public",
            "line": self._get_definition_line(symbol_info.symbol, doc),
        }

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
                    func_keywords = self.keyword_extractor.extract_keywords_simple(
                        func_text, top_n=10
                    )
                    if func_keywords:
                        func_data["keywords"] = func_keywords
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
        """
        for occurrence in doc.occurrences:
            # Check if this is the symbol and it's a definition (symbol_roles is a bitfield)
            if occurrence.symbol == symbol and (
                occurrence.symbol_roles & scip_pb2.SymbolRole.Definition
            ):
                return occurrence.range[0] if occurrence.range else 1

        return 1  # Fallback to line 1

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
            "language": "python",
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
