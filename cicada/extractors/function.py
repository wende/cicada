"""
Function extraction logic.
"""

from .base import get_param_name


def extract_functions(node, source_code: bytes) -> list:
    """Extract all function definitions from a module body."""
    functions = []
    _find_functions_recursive(node, source_code, functions)
    return functions


def _find_functions_recursive(node, source_code: bytes, functions: list):
    """Recursively find def and defp declarations."""
    # Check if this node is a function call (def or defp)
    if node.type == "call":
        # Get the target (function name)
        target = None
        arguments = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child

        # Check if this is a def or defp call
        if target and arguments:
            target_text = source_code[target.start_byte : target.end_byte].decode(
                "utf-8"
            )

            if target_text in ["def", "defp"]:
                # Extract function name and arity
                func_info = _parse_function_definition(
                    arguments, source_code, target_text, node.start_point[0] + 1
                )
                if func_info:
                    functions.append(func_info)
                    return  # Don't recurse into function body

    # Recursively process children
    for child in node.children:
        _find_functions_recursive(child, source_code, functions)


def _parse_function_definition(
    arguments_node, source_code: bytes, func_type: str, line: int
) -> dict:
    """Parse a function definition to extract name, arity, argument names, and guards."""
    func_name = None
    arity = 0
    arg_names = []
    guards = []

    for arg_child in arguments_node.children:
        # The function signature can be either:
        # 1. A call node (function with params): func_name(param1, param2)
        # 2. An identifier (function with no params): func_name
        # 3. A binary_operator (when guards are present): func_name(params) when guard
        if arg_child.type == "call":
            # Extract function name from call target
            for call_child in arg_child.children:
                if call_child.type == "identifier":
                    func_name = source_code[
                        call_child.start_byte : call_child.end_byte
                    ].decode("utf-8")
                elif call_child.type == "arguments":
                    arg_names = _extract_argument_names(call_child, source_code)
                    arity = len(arg_names)
            break
        elif arg_child.type == "binary_operator":
            # This handles guards: func_name(params) when guard_expr
            # The binary_operator contains the call as its first child
            for op_child in arg_child.children:
                if op_child.type == "call":
                    # Extract function name and args from the call
                    for call_child in op_child.children:
                        if call_child.type == "identifier":
                            func_name = source_code[
                                call_child.start_byte : call_child.end_byte
                            ].decode("utf-8")
                        elif call_child.type == "arguments":
                            arg_names = _extract_argument_names(call_child, source_code)
                            arity = len(arg_names)
                    break
            break
        elif arg_child.type == "identifier":
            func_name = source_code[arg_child.start_byte : arg_child.end_byte].decode(
                "utf-8"
            )
            arity = 0
            arg_names = []
            break

    # Extract guard clauses
    guards = _extract_guards(arguments_node, source_code)

    if func_name:
        return {
            "name": func_name,
            "arity": arity,
            "args": arg_names,
            "guards": guards,
            "full_name": f"{func_name}/{arity}",
            "line": line,
            "signature": f"{func_type} {func_name}",
            "type": func_type,
        }

    return None


def _extract_guards(arguments_node, source_code: bytes) -> list[str]:
    """
    Extract guard clauses from function definition arguments.

    Example:
        def abs_value(n) when n < 0, do: -n
        Returns: ["n < 0"]

    Tree structure:
        arguments:
          binary_operator:  # This contains function_call WHEN guard_expr
            call: abs_value(n)
            when: 'when'
            binary_operator: n < 0  # This is the guard expression
    """
    guards = []

    for arg_child in arguments_node.children:
        # Guards appear as binary_operator nodes containing 'when'
        if arg_child.type == "binary_operator":
            # Look for 'when' keyword and the guard expression after it
            has_when = False
            guard_node = None

            for op_child in arg_child.children:
                if op_child.type == "when":
                    has_when = True
                elif has_when:
                    # This is the guard expression node (comes after 'when')
                    # It's typically a binary_operator (like n < 0)
                    guard_expr = source_code[
                        op_child.start_byte : op_child.end_byte
                    ].decode("utf-8")
                    guards.append(guard_expr)
                    break

    return guards


def _extract_argument_names(params_node, source_code: bytes) -> list[str]:
    """Extract parameter names from function arguments."""
    arg_names = []

    for child in params_node.children:
        if child.type in [",", "(", ")", "[", "]"]:
            continue

        # Extract the argument name (simplified - handles basic cases)
        arg_name = get_param_name(child, source_code)
        if arg_name:
            arg_names.append(arg_name)

    return arg_names
