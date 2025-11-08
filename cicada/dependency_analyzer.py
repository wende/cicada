"""
Dependency analysis for Elixir modules and functions.

This module processes already-extracted AST data (aliases, imports, uses, calls)
to produce clean dependency information.
"""


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

    # 1. Add dependencies from aliases (use full names, not short names)
    for full_name in aliases.values():
        dependencies.add(full_name)

    # 2. Add dependencies from imports
    for import_name in module_data.get("imports", []):
        dependencies.add(import_name)

    # 3. Add dependencies from uses
    for use_name in module_data.get("uses", []):
        dependencies.add(use_name)

    # 4. Add dependencies from requires
    for require_name in module_data.get("requires", []):
        dependencies.add(require_name)

    # 5. Add dependencies from behaviours
    for behaviour_name in module_data.get("behaviours", []):
        dependencies.add(behaviour_name)

    # 6. Add dependencies from function calls (module references)
    for call in module_data.get("calls", []):
        module_name = call.get("module")
        if module_name:
            # Resolve alias if present
            resolved_module = aliases.get(module_name, module_name)

            # Exclude Kernel module (too noisy)
            if resolved_module != "Kernel":
                dependencies.add(resolved_module)

    return {
        "modules": sorted(list(dependencies)),
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
        if function_start_line <= call["line"] <= function_end_line
    ]

    dependencies = []

    for call in function_calls:
        call_module = call.get("module")
        call_function = call.get("function")
        call_arity = call.get("arity")
        call_line = call.get("line")

        # Resolve module name
        if call_module:
            # External call - resolve alias
            resolved_module = aliases.get(call_module, call_module)
        else:
            # Local call - use current module name
            resolved_module = module_name

        dependencies.append(
            {
                "module": resolved_module,
                "function": call_function,
                "arity": call_arity,
                "line": call_line,
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
    else:
        # Last function - use a large number as end line
        # This is a heuristic; ideally we'd get the actual end line from the AST
        return function_line + 10000
