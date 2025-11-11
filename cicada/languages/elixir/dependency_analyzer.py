"""
Dependency analysis for Elixir modules and functions.

This module processes already-extracted AST data (aliases, imports, uses, calls)
to produce clean dependency information.
"""


def _resolve_module_alias(module_name: str, aliases: dict) -> str:
    """
    Resolve a module name using the alias mapping.

    Args:
        module_name: Short or full module name
        aliases: Dict mapping short names to full names

    Returns:
        Full module name (resolved if aliased, otherwise unchanged)
    """
    return aliases.get(module_name, module_name)


def extract_module_dependencies(module_data: dict) -> dict:
    """
    Extract module-level dependencies from parsed module data.

    Args:
        module_data: Dictionary containing module information with:
            - aliases: Dict mapping short names to full module names
            - imports: List of imported module names
            - uses: List of used module names
            - requires: List of required module names (optional)
            - behaviours: List of behaviour module names (optional)
            - calls: List of function calls with module, function, arity, line

    Returns:
        Dictionary with:
            - modules: Set of module names this module depends on
            - has_dynamic_calls: Boolean indicating if there are unresolved calls
    """
    dependencies = set()
    aliases = module_data.get("aliases", {})

    # Add dependencies from various sources
    # Note: we use aliases.values() to get full names, not short names
    for _source_key, extract_values in [
        ("aliases", lambda: aliases.values()),
        ("imports", lambda: module_data.get("imports", [])),
        ("uses", lambda: module_data.get("uses", [])),
        ("requires", lambda: module_data.get("requires", [])),
        ("behaviours", lambda: module_data.get("behaviours", [])),
    ]:
        dependencies.update(extract_values())

    # Add dependencies from function calls (with alias resolution)
    for call in module_data.get("calls", []):
        module_name = call.get("module")
        if module_name:
            resolved_module = _resolve_module_alias(module_name, aliases)
            # Exclude Kernel module (too noisy)
            if resolved_module != "Kernel":
                dependencies.add(resolved_module)

    return {
        "modules": sorted(dependencies),
        "has_dynamic_calls": False,  # Could be enhanced to detect apply() etc.
    }


def extract_function_dependencies(
    module_data: dict,
    function_data: dict,
    all_module_calls: list,
    function_end_line: int,
) -> list:
    """
    Extract function-level dependencies from function calls.

    Args:
        module_data: Dictionary containing module information (for alias resolution)
        function_data: Dictionary containing function information (name, arity, line)
        all_module_calls: List of ALL calls in the module
        function_end_line: The line where the function ends

    Returns:
        List of dictionaries, each containing:
            - module: Module name (resolved from aliases)
            - function: Function name
            - arity: Function arity
            - line: Line number where called
    """
    module_name = module_data.get("module")
    aliases = module_data.get("aliases", {})
    function_start_line = function_data.get("line")

    # Filter calls to only those within this function's line range
    function_calls = [
        call
        for call in all_module_calls
        if function_start_line is not None
        and call.get("line") is not None
        and function_start_line <= call["line"] <= function_end_line
    ]

    dependencies = []
    for call in function_calls:
        # Resolve module name (external calls use aliases, local calls use current module)
        call_module = call.get("module")
        resolved_module = (
            _resolve_module_alias(call_module, aliases) if call_module else module_name
        )

        dependencies.append(
            {
                "module": resolved_module,
                "function": call.get("function"),
                "arity": call.get("arity"),
                "line": call.get("line"),
            }
        )

    return dependencies


def calculate_function_end_line(function_data: dict, next_function_line: int | None) -> int:
    """
    Calculate the end line of a function.

    Args:
        function_data: Dictionary containing function information
        next_function_line: Line number of the next function, or None if this is the last function

    Returns:
        Estimated end line of the function
    """
    function_line = function_data.get("line")

    if next_function_line:
        # Function ends just before the next function
        return next_function_line - 1
    elif function_line is not None:
        # Last function - use a large number as end line
        # This is a heuristic; ideally we'd get the actual end line from the AST
        return function_line + 10000
    else:
        # If no line info, return a large number
        return 99999999
