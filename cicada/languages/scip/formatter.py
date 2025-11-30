"""
Python-specific formatting utilities (via SCIP).

This module provides Python-specific formatting rules for function identifiers
and other language-specific display conventions.
"""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class PythonFormatter(BaseLanguageFormatter):
    """Formatter for Python language conventions."""

    # Args to filter from signatures (instance/class refs)
    # SCIP strips self/cls, but uses 'arg0' as placeholder when self was the only arg
    _IMPLICIT_ARGS = frozenset({"self", "cls", "arg0"})

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

    def format_function_name(
        self, func_name: str, arity: int, args: list[str] | None = None
    ) -> str:
        """
        Format function name with args, filtering out self/cls/arg0.

        Args:
            func_name: The function or method name
            arity: The number of parameters
            args: Optional list of argument names

        Returns:
            Formatted function name like "method(config)" or "method()"

        Examples:
            >>> formatter = PythonFormatter()
            >>> formatter.format_function_name("__init__", 1, ["config"])
            '__init__(config)'
            >>> formatter.format_function_name("index", 1, ["arg0"])
            'index()'
            >>> formatter.format_function_name("main", 0, [])
            'main()'
        """
        if args is not None:
            visible_args = [a for a in args if a not in self._IMPLICIT_ARGS]
            return f"{func_name}({', '.join(visible_args)})"
        return f"{func_name}()"
