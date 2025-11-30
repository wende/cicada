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
            Formatted function name like "map(List, Fun)" or "map/2"

        Examples:
            >>> formatter = ErlangFormatter()
            >>> formatter.format_function_name("map", 2, ["List", "Fun"])
            'map(List, Fun)'
            >>> formatter.format_function_name("map", 2)
            'map/2'
            >>> formatter.format_function_name("init", 0, [])
            'init/0'
        """
        if args:
            return f"{func_name}({', '.join(args)})"
        return f"{func_name}/{arity}"
