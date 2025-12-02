"""
Elixir-specific formatting utilities.

This module provides Elixir-specific formatting rules for function identifiers
and other language-specific display conventions.
"""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class ElixirFormatter(BaseLanguageFormatter):
    """Formatter for Elixir language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using Elixir's /arity notation.

        Args:
            module_name: The module name
            func_name: The function name
            arity: The number of parameters

        Returns:
            Formatted identifier like "MyModule.my_func/2"

        Examples:
            >>> formatter = ElixirFormatter()
            >>> formatter.format_function_identifier("MyModule", "add", 2)
            'MyModule.add/2'
        """
        return f"{module_name}.{func_name}/{arity}"

    def format_function_name(
        self, func_name: str, arity: int, args: list[str] | None = None
    ) -> str:
        """
        Format function name with args if available, otherwise arity.

        Args:
            func_name: The function name
            arity: The number of parameters
            args: Optional list of argument names

        Returns:
            Formatted function name like "add(a, b)" or "add/2"

        Examples:
            >>> formatter = ElixirFormatter()
            >>> formatter.format_function_name("add", 2, ["a", "b"])
            'add(a, b)'
            >>> formatter.format_function_name("add", 2)
            'add/2'
            >>> formatter.format_function_name("hello", 0, [])
            'hello/0'
        """
        if args:
            return f"{func_name}({', '.join(args)})"
        return f"{func_name}/{arity}"
