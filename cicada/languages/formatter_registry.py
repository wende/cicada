"""
Language formatter registry.

Provides a factory function to get the appropriate language-specific
formatter based on the language identifier.

This module delegates to LanguageRegistry.get_formatter() to ensure
all language definitions are centralized in one place.
"""

from cicada.languages.formatter_interface import BaseLanguageFormatter


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
    # Import here to avoid circular imports at module level
    from cicada.languages import LanguageNotSupportedError, LanguageRegistry

    try:
        return LanguageRegistry.get_formatter(language)
    except LanguageNotSupportedError:
        supported = LanguageRegistry.get_supported_languages()
        raise ValueError(f"Unsupported language: '{language}'. Supported: {supported}") from None
    except ValueError as e:
        # Re-raise with same message format for backwards compatibility
        supported = LanguageRegistry.get_supported_languages()
        raise ValueError(f"Unsupported language: '{language}'. Supported: {supported}") from e
