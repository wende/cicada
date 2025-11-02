"""
Tree-sitter utilities for extracting and analyzing tree nodes.

This module provides shared utilities for working with tree-sitter parse trees,
including extracting text from nodes and identifying function definitions.
"""


def extract_text_from_node(node, source_code: bytes) -> str:
    """
    Extract text from a tree-sitter node.

    Args:
        node: The tree-sitter node to extract text from
        source_code: The source code bytes that the node was parsed from

    Returns:
        The decoded text content of the node

    Examples:
        >>> text = extract_text_from_node(node, source_code)
        >>> text = extract_text_from_node(child_node, source_code)
    """
    return source_code[node.start_byte : node.end_byte].decode("utf-8")


def is_function_definition_call(call_node, source_code: bytes) -> bool:
    """
    Check if a call node represents a function definition (def, defp, or defmodule).

    Args:
        call_node: A tree-sitter call node
        source_code: The source code bytes that the node was parsed from

    Returns:
        True if the call is a function definition, False otherwise

    Examples:
        >>> if is_function_definition_call(node, source_code):
        ...     skip_processing()
    """
    for child in call_node.children:
        if child.type == "identifier":
            target_text = extract_text_from_node(child, source_code)
            if target_text in ["def", "defp", "defmodule"]:
                return True
    return False
