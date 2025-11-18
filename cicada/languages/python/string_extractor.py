"""
String literal extraction from Python source code.

This module extracts string literals from function bodies for keyword-based
indexing and search. It filters out docstrings and other non-relevant
string content.
"""

import ast
from typing import Any


class PythonStringExtractor:
    """Extract string literals from Python source code."""

    def __init__(self, min_length: int = 3):
        """
        Initialize the string extractor.

        Args:
            min_length: Minimum string length to extract (default: 3)
        """
        self.min_length = min_length

    def extract_from_source(self, source_code: str) -> list[dict]:
        """
        Extract all string literals from Python source code.

        Args:
            source_code: Python source code as string

        Returns:
            List of dicts containing:
                - string: The string content
                - line: Line number where the string appears
                - function: Name of the function containing the string (or None)
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        extractor = _StringVisitor(self.min_length)
        extractor.visit(tree)
        return extractor.strings


class _StringVisitor(ast.NodeVisitor):
    """AST visitor to extract string literals."""

    def __init__(self, min_length: int):
        self.min_length = min_length
        self.strings: list[dict] = []
        self.current_function: str | None = None
        self.docstring_lines: set[int] = set()

    def visit_Module(self, node: ast.Module) -> None:
        # Mark module docstring
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Mark class docstring
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Process a function definition."""
        # Mark function docstring
        self._mark_docstring(node)

        # Track function context
        prev_function = self.current_function
        self.current_function = node.name

        # Visit function body
        self.generic_visit(node)

        # Restore context
        self.current_function = prev_function

    def _mark_docstring(self, node: Any) -> None:
        """Mark the docstring line for a node if it has one."""
        if not hasattr(node, "body") or not node.body:
            return

        first_stmt = node.body[0]
        if (
            isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)
        ):
            self.docstring_lines.add(first_stmt.lineno)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Extract string constants."""
        if isinstance(node.value, str):
            # Skip docstrings
            if node.lineno in self.docstring_lines:
                return

            # Skip short strings
            if len(node.value) < self.min_length:
                return

            # Skip empty or whitespace-only strings
            if not node.value.strip():
                return

            self.strings.append(
                {
                    "string": node.value,
                    "line": node.lineno,
                    "function": self.current_function,
                }
            )

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Extract f-string content.

        For f-strings, we extract the static parts only,
        concatenated together.
        """
        static_parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                static_parts.append(str(value.value))  # type: ignore[arg-type]

        combined = "".join(static_parts)
        if len(combined) >= self.min_length and combined.strip():
            self.strings.append(
                {
                    "string": combined,
                    "line": node.lineno,
                    "function": self.current_function,
                }
            )

        # Still visit children for any nested strings
        self.generic_visit(node)
