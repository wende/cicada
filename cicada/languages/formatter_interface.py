"""
Formatter interface for language-specific formatting.

Each language implementation should provide its own formatter
that implements these methods.
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
