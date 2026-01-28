"""
Formatter interface for language-specific formatting.

Each language implementation should provide its own formatter
that implements these methods.

Note: This class is inlined here (rather than imported from cicada-mcp-core) so that
cicada-mcp can be installed standalone without requiring cicada-mcp-core. The canonical
source is packages/cicada-mcp-core/src/cicada_mcp_core/formatter_interface.py - keep both
in sync if changes are needed.
"""

from abc import ABC, abstractmethod


class BaseLanguageFormatter(ABC):
    """
    Abstract base class for language-specific formatters.

    Each language (Elixir, Python, etc.) should implement this interface
    to provide language-specific formatting rules.
    """

    @abstractmethod
    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """
        Format a function identifier in language-specific notation.

        Args:
            module_name: The module or class name
            func_name: The function or method name
            arity: The number of parameters

        Returns:
            Formatted function identifier string

        Examples:
            Elixir: "MyModule.my_func/2"
            Python: "MyClass.my_method()"
        """

    @abstractmethod
    def format_function_name(
        self, func_name: str, arity: int, args: list[str] | None = None
    ) -> str:
        """
        Format just the function name with args/arity (no module prefix).

        Args:
            func_name: The function or method name
            arity: The number of parameters
            args: Optional list of argument names

        Returns:
            Formatted function name string

        Examples:
            Elixir: "my_func(a, b)" or "my_func/2"
            Python: "my_method(config)" or "my_method()"
        """


__all__ = ["BaseLanguageFormatter"]
