"""
Shared utilities for extractors.
"""


def extract_string_from_arguments(arguments_node, source_code: bytes) -> str | None:
    """Extract string value from function arguments."""
    for child in arguments_node.children:
        # Handle string literals
        if child.type == "string":
            # Get the string content (without quotes)
            string_content = []
            for string_child in child.children:
                if string_child.type == "quoted_content":
                    content = source_code[string_child.start_byte : string_child.end_byte].decode(
                        "utf-8"
                    )
                    string_content.append(content)

            if string_content:
                return "".join(string_content)

        # Handle false (for @moduledoc false)
        elif child.type == "boolean" or child.type == "atom":
            value = source_code[child.start_byte : child.end_byte].decode("utf-8")
            if value == "false":
                return None

    return None


def get_param_name(node, source_code: bytes) -> str | None:
    """Get parameter name from a parameter node."""
    # Handle simple identifier: my_arg
    if node.type == "identifier":
        return source_code[node.start_byte : node.end_byte].decode("utf-8")

    # Handle pattern match with default: my_arg \\ default_value
    elif node.type == "binary_operator":
        for child in node.children:
            if child.type == "identifier":
                return source_code[child.start_byte : child.end_byte].decode("utf-8")

    # Handle destructuring: {key, value} or [head | tail]
    elif node.type in ["tuple", "list", "map"]:
        # For complex patterns, return the whole pattern as string
        return source_code[node.start_byte : node.end_byte].decode("utf-8")

    # Handle call patterns (e.g., %Struct{} = arg)
    elif node.type == "call":
        # Try to find the actual variable name
        for child in node.children:
            if child.type == "identifier":
                return source_code[child.start_byte : child.end_byte].decode("utf-8")

    # Fallback: return the whole node as string
    return source_code[node.start_byte : node.end_byte].decode("utf-8")


def count_arguments(arguments_node) -> int:
    """Count the number of arguments in a function call."""
    count = 0
    for child in arguments_node.children:
        if child.type not in [",", "(", ")"]:
            count += 1
    return count
