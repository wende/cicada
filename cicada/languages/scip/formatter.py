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

    # Args to filter from signatures (instance/class refs)
    # SCIP strips self/cls, but uses 'arg0' as placeholder when self was the only arg
    _IMPLICIT_ARGS = frozenset({"self", "cls", "arg0"})

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


class PythonFormatter(SCIPFormatter):
    """Formatter for Python language conventions."""


class TypeScriptFormatter(SCIPFormatter):
    """Formatter for TypeScript language conventions."""
