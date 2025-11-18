"""Elixir function signature extractor.

Extracts function signatures from Elixir source code for co-change analysis.
"""

import re

from cicada.extractors.base_signature import (
    FunctionSignatureExtractor,
    SignatureExtractorRegistry,
)

# Regex patterns for parsing Elixir code
# Note: Elixir allows ? and ! in function names (e.g., empty?, save!)
ELIXIR_FUNCTION_PATTERN = re.compile(
    r"^\s*def[p]?\s+([a-z_][a-z0-9_?!]*)\s*\(([^)]*)\)", re.MULTILINE
)
ELIXIR_MODULE_PATTERN = re.compile(r"defmodule\s+([A-Z][A-Za-z0-9_.]*)\s+do")


class ElixirSignatureExtractor(FunctionSignatureExtractor):
    """Extract function signatures from Elixir source code."""

    def get_file_extensions(self) -> list[str]:
        """Return Elixir file extensions.

        Returns:
            List containing .ex and .exs extensions
        """
        return [".ex", ".exs"]

    def extract_module_name(self, content: str, file_path: str) -> str | None:
        """Extract the module name from Elixir source code.

        Args:
            content: Elixir source code
            file_path: Path to file (unused for Elixir)

        Returns:
            Module name or None if not found
        """
        # Look for defmodule declaration using pre-compiled pattern
        module_match = ELIXIR_MODULE_PATTERN.search(content)
        if module_match:
            return module_match.group(1)
        return None

    def extract_function_signatures(self, content: str, module_name: str) -> set[str]:
        """Extract all function signatures from Elixir source code.

        Args:
            content: Elixir source code
            module_name: Module name for the functions

        Returns:
            Set of function signatures (e.g., {"ModuleName.func_name/2"})
        """
        # Module name should start with uppercase (Elixir convention)
        if not module_name or not module_name[0].isupper():
            return set()

        signatures = set()
        for match in ELIXIR_FUNCTION_PATTERN.finditer(content):
            func_name = match.group(1)
            # Function name should start with lowercase (Elixir convention)
            if func_name and func_name[0].islower():
                arity = self._calculate_arity(match.group(2))
                signatures.add(f"{module_name}.{func_name}/{arity}")

        return signatures

    def _calculate_arity(self, params: str) -> int:
        """Calculate function arity from parameter string.

        Uses a simple comma-counting heuristic that works for most cases.

        Args:
            params: Function parameter string from regex match

        Returns:
            Approximate arity (parameter count)
        """
        if not params.strip():
            return 0
        return len([p for p in params.split(",") if p.strip()])


# Register the extractor
SignatureExtractorRegistry.register("elixir", ElixirSignatureExtractor)
