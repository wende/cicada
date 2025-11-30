"""Extract import aliases from Python source files using AST."""

import ast
from pathlib import Path


class PythonAliasExtractor:
    """
    Extract import alias mappings from Python source files.

    Handles:
    - import operations as ops → {"ops": "operations"}
    - from utils import average as avg → {"avg": "utils"} (module-level tracking)
    - from calculator import Calculator as Calc → {"Calc": "calculator"}
    """

    def extract_aliases(self, file_path: Path | str) -> dict[str, str]:
        """
        Extract alias mappings from a Python file.

        Args:
            file_path: Path to Python source file

        Returns:
            Dictionary mapping alias names to full module names
            Example: {"ops": "operations", "avg": "utils", "Calc": "calculator"}
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            return self.extract_aliases_from_source(source)
        except (OSError, UnicodeDecodeError):
            # If file cannot be read, return empty dict
            return {}

    def extract_aliases_from_source(self, source: str) -> dict[str, str]:
        """
        Extract alias mappings from Python source code.

        Args:
            source: Python source code as string

        Returns:
            Dictionary mapping alias names to module names
        """
        aliases = {}

        try:
            tree = ast.parse(source)
        except SyntaxError:
            # If source has syntax errors, return empty dict
            return {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import operations as ops
                for alias in node.names:
                    if alias.asname:  # Only track if there's an alias
                        aliases[alias.asname] = alias.name

            elif isinstance(node, ast.ImportFrom) and node.module:
                # Handle: from utils import average as avg
                # We track at module level: {"avg": "utils"}
                # This matches how Elixir aliases work (module-level)
                for alias in node.names:
                    if alias.asname:  # Only track if there's an alias
                        # Map the alias to the source module
                        # For "from X import Y as Z", we map "Z" -> "X"
                        aliases[alias.asname] = node.module
                    elif alias.name != "*":
                        # Also track direct imports without alias
                        # "from X import Y" → implicit alias "Y" -> "X"
                        # This helps track usage even without explicit aliases
                        aliases[alias.name] = node.module

        return aliases

    def get_module_for_alias(self, alias_name: str, aliases: dict[str, str]) -> str | None:
        """
        Resolve an alias name to its full module name.

        Args:
            alias_name: The alias to resolve (e.g., "ops", "avg")
            aliases: The alias mapping dictionary

        Returns:
            Full module name or None if not found
        """
        return aliases.get(alias_name)
