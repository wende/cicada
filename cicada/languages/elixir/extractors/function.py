"""
Function extraction logic.

Author: Cursor(Auto)
"""

from cicada.utils import extract_text_from_node

from .base import extract_string_from_arguments, get_param_name


def extract_functions(node, source_code: bytes) -> list:
    """Extract all function definitions from a module body."""
    functions = []
    _find_functions_recursive(node, source_code, functions)
    return functions


def _extract_impl_from_prev_sibling(node, source_code: bytes):
    """
    Extract @impl value from previous sibling if it's an @impl attribute.

    Returns:
        - True if @impl true
        - Module name (str) if @impl ModuleName
        - None if not an @impl attribute
    """
    if node is None or node.type != "unary_operator":
        return None

    # Check if this is an @ operator
    is_at_operator = False
    impl_call = None

    for child in node.children:
        if child.type == "@":
            is_at_operator = True
        elif child.type == "call" and is_at_operator:
            impl_call = child
            break

    if not impl_call:
        return None

    # Check if the call is "impl"
    identifier_text = None
    arguments_node = None

    for child in impl_call.children:
        if child.type == "identifier":
            identifier_text = extract_text_from_node(child, source_code)
        elif child.type == "arguments":
            arguments_node = child

    if identifier_text != "impl":
        return None

    # Extract the impl value from arguments
    if arguments_node:
        for arg_child in arguments_node.children:
            if arg_child.type == "boolean":
                # @impl true or @impl false
                bool_text = extract_text_from_node(arg_child, source_code)
                return bool_text == "true"
            elif arg_child.type == "alias":
                # @impl ModuleName
                module_name = extract_text_from_node(arg_child, source_code)
                return module_name

    # @impl without arguments defaults to true
    return True


def _find_functions_recursive(node, source_code: bytes, functions: list):
    """Recursively find def, defp, and test declarations."""
    # Track previous sibling to detect @impl attributes
    prev_sibling = None

    # Iterate through children to process siblings
    for child in node.children:
        # Check if this child is a function call (def, defp, or test)
        if child.type == "call":
            # Get the target (function name)
            target = None
            arguments = None

            for call_child in child.children:
                if call_child.type == "identifier":
                    target = call_child
                elif call_child.type == "arguments":
                    arguments = call_child

            # Check if this is a def, defp, or test call
            if target and arguments:
                target_text = extract_text_from_node(target, source_code)

                if target_text in ["def", "defp"]:
                    # Check if previous sibling is @impl
                    impl_value = _extract_impl_from_prev_sibling(prev_sibling, source_code)

                    # Extract function name and arity
                    func_info = _parse_function_definition(
                        arguments, source_code, target_text, child.start_point[0] + 1
                    )
                    if func_info:
                        # Add impl attribute if present
                        if impl_value is not None:
                            func_info["impl"] = impl_value
                        else:
                            func_info["impl"] = False
                        functions.append(func_info)
                        prev_sibling = child
                        continue  # Don't recurse into function body
                elif target_text == "test":
                    # Handle test macro: test "description" do ... end
                    func_info = _parse_test_definition(
                        arguments, source_code, child.start_point[0] + 1
                    )
                    if func_info:
                        functions.append(func_info)
                        prev_sibling = child
                        continue  # Don't recurse into test body

        # Recursively process this child
        _find_functions_recursive(child, source_code, functions)
        prev_sibling = child


def _parse_test_definition(arguments_node, source_code: bytes, line: int) -> dict | None:
    """
    Parse a test macro definition to extract the test description.

    Test syntax: test "description" do ... end

    Returns a function info dict with:
    - name: "test: <description>"
    - arity: 0 (context is implicitly passed)
    - line: line number
    - test_description: the full description string
    """
    test_description = extract_string_from_arguments(arguments_node, source_code)

    if test_description:
        # Generate a function name from the description
        # Use "test: " prefix to distinguish from regular functions
        func_name = f"test: {test_description}"

        return {
            "name": func_name,
            "arity": 0,  # Tests take context implicitly
            "args": [],
            "guards": [],
            "full_name": f"{func_name}/0",
            "line": line,
            "signature": f'test "{test_description}"',
            "type": "test",
            "visibility": "private",  # Tests are not part of public API
            "test_description": test_description,
            "impl": False,
        }

    return None


def _parse_function_definition(
    arguments_node, source_code: bytes, func_type: str, line: int
) -> dict | None:
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
                    func_name = extract_text_from_node(call_child, source_code)
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
                            func_name = extract_text_from_node(call_child, source_code)
                        elif call_child.type == "arguments":
                            arg_names = _extract_argument_names(call_child, source_code)
                            arity = len(arg_names)
                    break
            break
        elif arg_child.type == "identifier":
            func_name = extract_text_from_node(arg_child, source_code)
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
            "visibility": "public" if func_type == "def" else "private",
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

            for op_child in arg_child.children:
                if op_child.type == "when":
                    has_when = True
                elif has_when:
                    # This is the guard expression node (comes after 'when')
                    # It's typically a binary_operator (like n < 0)
                    guard_expr = extract_text_from_node(op_child, source_code)
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
