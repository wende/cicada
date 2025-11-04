"""
Module extraction logic.
"""

from cicada.utils import extract_text_from_node

from .base import extract_string_from_arguments


def extract_modules(root_node, source_code: bytes) -> list:
    """Extract all modules from the syntax tree."""
    modules = []
    _find_modules_recursive(root_node, source_code, modules)
    return modules


def _find_modules_recursive(node, source_code: bytes, modules: list):
    """Recursively find defmodule declarations."""
    # Check if this node is a function call (defmodule)
    if node.type == "call":
        # Get the target, arguments, and do_block (all siblings)
        target = None
        arguments = None
        do_block = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child
            elif child.type == "do_block":
                do_block = child

        # Check if this is a defmodule call
        if target and arguments:
            target_text = extract_text_from_node(target, source_code)

            if target_text == "defmodule":
                # Extract module name from arguments
                module_name = None

                for arg_child in arguments.children:
                    if arg_child.type == "alias":
                        module_name = extract_text_from_node(arg_child, source_code)
                        break

                if module_name and do_block:
                    module_info = {
                        "module": module_name,
                        "line": node.start_point[0] + 1,
                        "moduledoc": extract_moduledoc(do_block, source_code),
                        "do_block": do_block,  # Store for further extraction
                    }
                    modules.append(module_info)
                    return  # Don't recurse into module body

    # Recursively process children
    for child in node.children:
        _find_modules_recursive(child, source_code, modules)


def extract_moduledoc(node, source_code: bytes) -> str | None:
    """Extract the @moduledoc attribute from a module's do_block."""
    return _find_moduledoc_recursive(node, source_code)


def _find_moduledoc_recursive(node, source_code: bytes) -> str | None:
    """Recursively search for @moduledoc attribute."""
    # Look for unary_operator nodes (which represent @ attributes)
    if node.type == "unary_operator":
        operator = None
        operand = None

        for child in node.children:
            if child.type == "@":
                operator = child
            elif child.type == "call":
                # @moduledoc "..." is represented as a call
                operand = child

        if operator and operand:
            # Check if this is a moduledoc attribute
            for call_child in operand.children:
                if call_child.type == "identifier":
                    attr_name = extract_text_from_node(call_child, source_code)

                    if attr_name == "moduledoc":
                        # Extract the documentation string from the arguments
                        for arg_child in operand.children:
                            if arg_child.type == "arguments":
                                doc_string = extract_string_from_arguments(arg_child, source_code)
                                if doc_string:
                                    return doc_string

    # Recursively search children (only in the immediate do_block, not nested modules)
    for child in node.children:
        # Don't recurse into nested defmodule
        if child.type == "call":
            # Check if it's a defmodule
            is_defmodule = False
            for call_child in child.children:
                if call_child.type == "identifier":
                    target_text = extract_text_from_node(call_child, source_code)
                    if target_text == "defmodule":
                        is_defmodule = True
                        break

            if is_defmodule:
                continue

        result = _find_moduledoc_recursive(child, source_code)
        if result:
            return result

    return None
