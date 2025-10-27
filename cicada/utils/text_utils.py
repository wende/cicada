"""
Text utilities for identifier manipulation and processing.

This module provides shared utilities for working with code identifiers,
including splitting camelCase, PascalCase, and snake_case identifiers.
"""

import re
from typing import List


def split_identifier(identifier: str, lowercase: bool = True) -> List[str]:
    """
    Split an identifier by camelCase, PascalCase, and snake_case.

    Handles various identifier patterns:
    - snake_case: get_user_data -> ['get', 'user', 'data']
    - camelCase: getUserData -> ['get', 'user', 'data']
    - PascalCase: UserController -> ['user', 'controller']
    - HTTPServer: HTTP Server -> ['http', 'server']
    - PostgreSQL: Postgre SQL -> ['postgre', 'sql']
    - getHTTPResponseCode -> ['get', 'http', 'response', 'code']

    Args:
        identifier: The identifier string to split
        lowercase: If True, convert all words to lowercase (default: True)

    Returns:
        List of words from the identifier

    Examples:
        >>> split_identifier("getUserData")
        ['get', 'user', 'data']
        >>> split_identifier("HTTPServer")
        ['http', 'server']
        >>> split_identifier("snake_case_name")
        ['snake', 'case', 'name']
    """
    if not identifier:
        return []

    # Handle snake_case
    text = identifier.replace("_", " ")

    # Split on transitions from lowercase to uppercase (camelCase)
    # This handles: camelCase, PascalCase, and words ending with uppercase like PostgreSQL
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # Split on transitions from uppercase sequence to a capitalized word (HTTPServer -> HTTP Server)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)

    # Split consecutive uppercase letters to separate potential acronyms
    # This helps extract individual letters from acronyms at the end (e.g., SQL -> S Q L)
    # But only if they're part of a longer word (not standalone acronyms)
    text = re.sub(r"(?<=[a-z])([A-Z])(?=[A-Z])", r" \1", text)

    # Split and filter
    words = text.split()

    if lowercase:
        words = [word.lower() for word in words if word]
    else:
        words = [word for word in words if word]

    return words


def split_camel_snake_case(text: str) -> str:
    """
    Split camelCase, PascalCase, and snake_case identifiers into separate words as a string.

    This is a convenience wrapper around split_identifier() that returns a space-separated
    string instead of a list.

    Args:
        text: Input text containing identifiers

    Returns:
        String with identifiers split into separate words

    Examples:
        >>> split_camel_snake_case("camelCase")
        'camel case'
        >>> split_camel_snake_case("PascalCase")
        'pascal case'
        >>> split_camel_snake_case("snake_case")
        'snake case'
    """
    words = split_identifier(text, lowercase=True)
    return " ".join(words)
