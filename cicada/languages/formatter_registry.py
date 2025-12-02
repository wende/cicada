"""
Language formatter registry.

Provides a factory function to get the appropriate language-specific
formatter based on the language identifier.
"""

from cicada.languages.elixir.formatter import ElixirFormatter
from cicada.languages.erlang.formatter import ErlangFormatter
from cicada.languages.formatter_interface import BaseLanguageFormatter
from cicada.languages.scip.formatter import PythonFormatter, TypeScriptFormatter


def get_language_formatter(language: str) -> BaseLanguageFormatter:
    """
    Get the appropriate language formatter based on language identifier.

    Args:
        language: Language identifier ('elixir', 'python', etc.)

    Returns:
        Language-specific formatter instance

    Raises:
        ValueError: If language is not supported

    Examples:
        >>> formatter = get_language_formatter('python')
        >>> formatter.format_function_identifier('MyClass', 'method', 2)
        'MyClass.method()'

        >>> formatter = get_language_formatter('elixir')
        >>> formatter.format_function_identifier('MyModule', 'func', 2)
        'MyModule.func/2'
    """
    formatters = {
        "elixir": ElixirFormatter(),
        "erlang": ErlangFormatter(),
        "python": PythonFormatter(),
        "typescript": TypeScriptFormatter(),
    }

    if language not in formatters:
        raise ValueError(
            f"Unsupported language: '{language}'. Supported: {list(formatters.keys())}"
        )

    return formatters[language]
