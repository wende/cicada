"""
Python and TypeScript formatting utilities (via SCIP).

This module provides Python and TypeScript-specific formatting rules for function
identifiers and other language-specific display conventions.

Both Python and TypeScript use the same () notation for function identifiers,
regardless of arity.
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


class TypeScriptFormatter(BaseLanguageFormatter):
    """Formatter for TypeScript language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using TypeScript's () notation.

        Note: TypeScript doesn't use arity in function identifiers - all functions
        use parentheses regardless of parameter count.

        Args:
            module_name: The class or module name
            func_name: The function or method name
            arity: The number of parameters (not used in TypeScript notation)

        Returns:
            Formatted identifier like "MyClass.my_method()"

        Examples:
            >>> formatter = TypeScriptFormatter()
            >>> formatter.format_function_identifier("Container", "add", 1)
            'Container.add()'
            >>> formatter.format_function_identifier("AsyncHandler", "save", 2)
            'AsyncHandler.save()'
        """
        return f"{module_name}.{func_name}()"
