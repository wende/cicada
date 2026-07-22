"""Gleam-specific formatting utilities."""

from cicada.languages.formatter_interface import BaseLanguageFormatter


class GleamFormatter(BaseLanguageFormatter):
    """Formatter for Gleam language conventions."""

    def format_function_identifier(self, module_name: str, func_name: str, arity: int) -> str:
        """Format a fully-qualified Gleam function identifier."""
        return f"{module_name}.{func_name}/{arity}"

    def format_function_name(
        self, func_name: str, arity: int, args: list[str] | None = None
    ) -> str:
        """Format a Gleam function name with arguments when available."""
        if args:
            return f"{func_name}({', '.join(args)})"
        return f"{func_name}/{arity}"
