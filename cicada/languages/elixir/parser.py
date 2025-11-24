"""
Elixir Parser using tree-sitter.

Parses Elixir source files to extract modules and functions.

Author: Cursor(Auto)
"""

import tree_sitter_elixir as ts_elixir
from tree_sitter import Language, Parser

from .extractors import (
    extract_aliases,
    extract_behaviours,
    extract_docs,
    extract_function_calls,
    extract_functions,
    extract_imports,
    extract_modules,
    extract_requires,
    extract_specs,
    extract_uses,
    extract_value_mentions,
    match_docs_to_functions,
    match_specs_to_functions,
)


class ElixirParser:
    """Parser for extracting modules and functions from Elixir files."""

    def __init__(self):
        """Initialize the tree-sitter parser with Elixir grammar."""
        self.parser = Parser(Language(ts_elixir.language()))  # type: ignore[deprecated]

    def parse_file(self, file_path: str) -> list[dict] | None:
        """
        Parse an Elixir file and extract module and function information.

        Args:
            file_path: Path to the .ex or .exs file to parse

        Returns:
            Dictionary containing module name and functions list, or None if parsing fails
        """
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()

            tree = self.parser.parse(source_code)
            root_node = tree.root_node

            # Check for parse errors
            if root_node.has_error:
                print(f"Parse error in {file_path}")
                return None

            # Extract all modules
            modules = extract_modules(root_node, source_code)

            if not modules:
                return None

            # Process each module to extract additional information
            for module_info in modules:
                do_block = module_info.pop("do_block")  # Remove do_block from result

                # Extract functions and specs
                functions = extract_functions(do_block, source_code)
                specs = extract_specs(do_block, source_code)

                # Match specs with functions
                functions_with_specs = match_specs_to_functions(functions, specs)

                # Extract and match docs
                docs = extract_docs(do_block, source_code)
                match_docs_to_functions(functions_with_specs, docs)

                # Extract dependencies
                aliases = extract_aliases(do_block, source_code)
                imports = extract_imports(do_block, source_code)
                requires = extract_requires(do_block, source_code)
                uses = extract_uses(do_block, source_code)
                behaviours = extract_behaviours(do_block, source_code)

                # Extract function calls and value mentions
                function_calls = extract_function_calls(do_block, source_code)
                value_mentions = extract_value_mentions(do_block, source_code)

                # Add all extracted information to module_info
                module_info["functions"] = functions_with_specs
                module_info["aliases"] = aliases
                module_info["imports"] = imports
                module_info["requires"] = requires
                module_info["uses"] = uses
                module_info["behaviours"] = behaviours
                module_info["value_mentions"] = value_mentions
                module_info["calls"] = function_calls

            return modules if modules else None

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            import traceback

            traceback.print_exc()
            return None


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) > 1:
        parser = ElixirParser()
        result = parser.parse_file(sys.argv[1])
        if result:
            import json

            print(json.dumps(result, indent=2))
        else:
            print("Failed to parse file")
    else:
        print("Usage: python parser.py <elixir_file.ex>")
