"""
Shared utilities for extractors.
"""

from cicada.utils import extract_text_from_node


def extract_string_from_arguments(arguments_node, source_code: bytes) -> str | None:
    """Extract string value from function arguments."""
    for child in arguments_node.children:
        # Handle string literals
        if child.type == "string":
            # Get the string content (without quotes)
            string_content = []
            for string_child in child.children:
                if string_child.type == "quoted_content":
                    content = extract_text_from_node(string_child, source_code)
                    string_content.append(content)

            if string_content:
                return "".join(string_content)

        # Handle false (for @moduledoc false)
        elif child.type == "boolean" or child.type == "atom":
            value = extract_text_from_node(child, source_code)
            if value == "false":
                return None

    return None


def get_param_name(node, source_code: bytes) -> str | None:
    """Get parameter name from a parameter node."""
    # Handle simple identifier: my_arg
    if node.type == "identifier":
        return extract_text_from_node(node, source_code)

    # Handle pattern match with default: my_arg \\ default_value
    elif node.type == "binary_operator":
        for child in node.children:
            if child.type == "identifier":
                return extract_text_from_node(child, source_code)

    # Handle destructuring: {key, value} or [head | tail]
    elif node.type in ["tuple", "list", "map"]:
        # For complex patterns, return the whole pattern as string
        return extract_text_from_node(node, source_code)

    # Handle call patterns (e.g., %Struct{} = arg)
    elif node.type == "call":
        # Try to find the actual variable name
        for child in node.children:
            if child.type == "identifier":
                return extract_text_from_node(child, source_code)

    # Fallback: return the whole node as string
    return extract_text_from_node(node, source_code)


def count_arguments(arguments_node) -> int:
    """Count the number of arguments in a function call."""
    count = 0
    for child in arguments_node.children:
        if child.type not in [",", "(", ")"]:
            count += 1
    return count
