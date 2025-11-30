"""Erlang-specific formatting utilities."""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class ErlangFormatter(BaseLanguageFormatter):
    """Formatter for Erlang language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier using Erlang's module:func/arity notation.

        Args:
            module_name: The module name
            func_name: The function name
            arity: The number of parameters

        Returns:
            Formatted identifier like "my_module:my_func/2"

        Examples:
            >>> formatter = ErlangFormatter()
            >>> formatter.format_function_identifier("lists", "map", 2)
            'lists:map/2'
        """
        return f"{module_name}:{func_name}/{arity}"
