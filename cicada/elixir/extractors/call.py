"""
Function call and value mention extraction logic.
"""

from cicada.utils import extract_text_from_node, is_function_definition_call

from .base import count_arguments


def extract_function_calls(node, source_code: bytes) -> list:
    """Extract all function calls from a module body."""
    calls = []
    _find_function_calls_recursive(node, source_code, calls)
    return calls


def _find_function_calls_recursive(node, source_code: bytes, calls: list):
    """Recursively find function calls."""
    # Skip module attributes (@spec, @doc, @moduledoc, @type, etc.)
    # These are wrapped in unary_operator nodes with @ token
    if node.type == "unary_operator":
        # Check if this is a module attribute (starts with @)
        for child in node.children:
            if child.type == "@":
                # This is a module attribute, skip the entire subtree
                return

    if node.type == "call":
        # Check if this is a function definition (def/defp)
        if is_function_definition_call(node, source_code):
            # Skip the arguments (which contain the function signature)
            # but still process the do_block to find calls within the function body
            for child in node.children:
                if child.type == "do_block":
                    _find_function_calls_recursive(child, source_code, calls)
            return  # Don't process other children

        # Try to extract the function call information
        call_info = _parse_function_call(node, source_code)
        if call_info:
            calls.append(call_info)

    # Recursively search all children
    for child in node.children:
        _find_function_calls_recursive(child, source_code, calls)


def _parse_function_call(call_node, source_code: bytes) -> dict | None:
    """
    Parse a function call to extract the module, function name, arity, and location.

    Handles:
    - Local calls: func(arg1, arg2)
    - Module calls: MyModule.func(arg1, arg2)
    - Aliased calls: User.create(name, email)
    """
    line = call_node.start_point[0] + 1

    # Check for dot notation (Module.function)
    has_dot = False
    module_name = None
    function_name = None
    arguments_node = None

    for child in call_node.children:
        if child.type == "dot":
            has_dot = True
            # Extract module and function from dot
            for dot_child in child.children:
                if dot_child.type == "alias":
                    module_name = extract_text_from_node(dot_child, source_code)
                elif dot_child.type == "identifier":
                    function_name = extract_text_from_node(dot_child, source_code)
        elif child.type == "identifier" and not has_dot:
            # Local function call
            function_name = extract_text_from_node(child, source_code)
        elif child.type == "arguments":
            arguments_node = child

    # Skip certain special forms and macros
    if function_name in [
        "alias",
        "import",
        "require",
        "use",
        "def",
        "defp",
        "defmodule",
        "if",
        "unless",
        "case",
        "cond",
        "with",
        "for",
        "try",
        "receive",
    ]:
        return None

    # Calculate arity
    arity = 0
    if arguments_node:
        arity = count_arguments(arguments_node)

    if function_name:
        return {
            "module": module_name,  # None for local calls
            "function": function_name,
            "arity": arity,
            "line": line,
        }

    return None


def extract_value_mentions(node, source_code: bytes) -> list:
    """Extract all module mentions as values (e.g., module passed as argument)."""
    value_mentions = []
    _find_value_mentions_recursive(node, source_code, value_mentions)
    # Return unique module names
    return list(set(value_mentions))


def _find_value_mentions_recursive(node, source_code: bytes, value_mentions: list):
    """Recursively find module value mentions."""
    # Look for alias nodes that are NOT part of alias/import/require/use declarations
    # and are NOT part of module function calls (which are already tracked in calls)

    if node.type == "alias":
        # Check if this is a standalone alias (value mention)
        # Skip if parent is a specific call type

        # Get the module name
        module_name = extract_text_from_node(node, source_code)

        # We need to check if this alias is part of a call with dot notation
        # If it has a dot parent, it's a module function call, not a value mention
        is_in_call = False
        current = node

        # Check ancestors to see if we're in a special context
        for _ in range(3):  # Check up to 3 levels up
            if current.parent:
                current = current.parent
                if current.type == "call":
                    # Check if this is alias/import/require/use/defmodule
                    for child in current.children:
                        if child.type == "identifier":
                            func_text = extract_text_from_node(child, source_code)
                            if func_text in [
                                "alias",
                                "import",
                                "require",
                                "use",
                                "defmodule",
                            ]:
                                is_in_call = True
                                break
                elif current.type == "dot":
                    # This alias is part of a Module.function call
                    is_in_call = True
                    break

        if not is_in_call:
            value_mentions.append(module_name)

    # Recursively search all children
    for child in node.children:
        _find_value_mentions_recursive(child, source_code, value_mentions)
