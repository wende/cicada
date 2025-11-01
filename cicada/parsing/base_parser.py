"""
Abstract base class for language-specific parsers.

All language implementations must subclass BaseParser and implement the abstract methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """
    Universal parser interface for all programming languages.

    Each language-specific parser (e.g., ElixirParser, PythonParser) must
    inherit from this class and implement all abstract methods.
    """

    @abstractmethod
    def parse_file(self, file_path: str | Path) -> list[dict] | None:
        """
        Parse a source file and extract module/class data.

        Args:
            file_path: Absolute path to the source file to parse

        Returns:
            List of module/class dictionaries with structure:
                {
                    "name": str,              # Module/class name
                    "file": str,              # File path
                    "line": int,              # Line number
                    "doc": str,               # Documentation
                    "functions": list[dict],  # Function definitions
                    "dependencies": list[dict],  # Imports/requires
                    "calls": list[dict],      # Function calls
                    "language_specific": dict # Extra language data
                }

            Returns None if parsing fails or file contains no indexable content.
        """

    @abstractmethod
    def get_language_name(self) -> str:
        """
        Return the language identifier for this parser.

        Returns:
            Language name in lowercase (e.g., 'elixir', 'python', 'typescript')
        """

    @abstractmethod
    def get_tree_sitter_language(self):
        """
        Return the tree-sitter Language instance for this parser.

        Returns:
            tree_sitter.Language instance configured for this language's grammar
        """

    def validate_file(self, file_path: str | Path) -> bool:
        """
        Check if a file should be parsed (optional override).

        Default implementation returns True. Override to implement custom
        validation logic (e.g., skip test files, check file size, etc.).

        Args:
            file_path: Path to validate

        Returns:
            True if file should be parsed, False otherwise
        """
        return True

    def get_file_extensions(self) -> list[str]:
        """
        Return file extensions this parser handles (optional override).

        Default implementation returns empty list. Override if you want
        to specify extensions at the parser level.

        Returns:
            List of file extensions including dots (e.g., ['.ex', '.exs'])
        """
        return []
