"""
Python-specific formatting utilities (via SCIP).

This module provides Python-specific formatting rules for function identifiers
and other language-specific display conventions.
"""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class PythonFormatter(BaseLanguageFormatter):
    """Formatter for Python language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using Python's () notation.

        Note: Python doesn't use arity in function identifiers - all functions
        use parentheses regardless of parameter count.

        Args:
            module_name: The class or module name
            func_name: The function or method name
            arity: The number of parameters (not used in Python notation)

        Returns:
            Formatted identifier like "MyClass.my_method()"

        Examples:
            >>> formatter = PythonFormatter()
            >>> formatter.format_function_identifier("MyClass", "my_method", 2)
            'MyClass.my_method()'
            >>> formatter.format_function_identifier("MyClass", "no_args", 0)
            'MyClass.no_args()'
        """
        return f"{module_name}.{func_name}()"
