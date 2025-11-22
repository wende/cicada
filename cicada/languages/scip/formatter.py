"""
SCIP-based language formatters (Python, TypeScript).

This module provides formatting rules for SCIP-indexed languages that share
common formatting conventions. Both Python and TypeScript use () notation
for function identifiers, regardless of arity.
"""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class SCIPFormatter(BaseLanguageFormatter):
    """
    Base formatter for SCIP-indexed languages (Python, TypeScript).

    SCIP-indexed languages use the same () notation for function identifiers,
    ignoring arity. This is different from Elixir which uses /arity notation.
    """

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using () notation.

        Note: SCIP-indexed languages don't use arity in function identifiers.
        All functions use parentheses regardless of parameter count.

        Args:
            module_name: The class or module name
            func_name: The function or method name
            arity: The number of parameters (ignored for SCIP languages)

        Returns:
            Formatted identifier like "MyClass.my_method()"

        Examples:
            >>> formatter = SCIPFormatter()
            >>> formatter.format_function_identifier("MyClass", "method", 2)
            'MyClass.method()'
            >>> formatter.format_function_identifier("Container", "add", 0)
            'Container.add()'
        """
        return f"{module_name}.{func_name}()"


class PythonFormatter(SCIPFormatter):
    """Formatter for Python language conventions."""


class TypeScriptFormatter(SCIPFormatter):
    """Formatter for TypeScript language conventions."""
