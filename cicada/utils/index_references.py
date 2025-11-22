"""
Index reference utilities for analyzing call sites and dependencies.

Provides functions to find callers, callees, dependencies, and references.
"""

from typing import Any

from cicada.utils.index_lookup import lookup_module


def get_call_sites(
    index: dict[str, Any],
    module_name: str,
    function_name: str,
) -> list[dict[str, Any]]:
    """
    Get all call sites for a specific function.

    Args:
        index: Index dictionary
        module_name: Name of the module containing the function
        function_name: Name of the function

    Returns:
        List of call site dictionaries with caller location info

    Example:
        sites = get_call_sites(index, "Calculator", "add")
        for site in sites:
            print(f"Called from {site['file']}:{site['line']}")
    """
    module = lookup_module(index, module_name)
    if not module:
        return []

    for func in module.get("functions", []):
        if func.get("name") == function_name:
            # Return dependencies instead of calls (SCIP format)
            # Dependencies have {module, function, arity, line}
            # Calls have {callee, file, line} (raw SCIP symbols)
            return func.get("dependencies", func.get("calls", []))

    return []


def get_callers_of(
    index: dict[str, Any],
    function_name: str,
) -> list[dict[str, Any]]:
    """
    Find all functions that call the specified function.

    Args:
        index: Index dictionary
        function_name: Name of the function being called

    Returns:
        List of dicts with caller information (module, function, line)

    Example:
        callers = get_callers_of(index, "len")
        for caller in callers:
            print(f"Called by {caller['module']}.{caller['function']}")
    """
    callers = []

    if "modules" not in index:
        return callers

    # Search all functions for calls to target
    for module_name, module_data in index["modules"].items():
        for func in module_data.get("functions", []):
            # Use dependencies instead of calls (SCIP format)
            # Dependencies have {module, function, arity, line}
            # Calls have {callee, file, line} (raw SCIP symbols)
            calls = func.get("dependencies", func.get("calls", []))

            for call in calls:
                callee = call.get("callee", call.get("function", call.get("symbol")))

                # Check if this call is to our target function
                if callee and function_name in callee:
                    callers.append(
                        {
                            "module": module_name,
                            "function": func["name"],
                            "line": call.get("line", call.get("caller_line")),
                            "file": call.get(
                                "file", call.get("caller_file", module_data.get("file"))
                            ),
                        }
                    )

    return callers


def get_callees_of(
    index: dict[str, Any],
    module_name: str,
    function_name: str,
) -> list[dict[str, Any]]:
    """
    Get all functions called by the specified function.

    Args:
        index: Index dictionary
        module_name: Name of the module containing the function
        function_name: Name of the calling function

    Returns:
        List of dicts with callee information

    Example:
        callees = get_callees_of(index, "Calculator", "process")
        for callee in callees:
            print(f"Calls {callee['function']}")
    """
    call_sites = get_call_sites(index, module_name, function_name)

    callees = []
    for call in call_sites:
        callee_name = call.get("callee", call.get("function", call.get("symbol")))
        if callee_name:
            callees.append(
                {
                    "function": callee_name,
                    "line": call.get("line"),
                    "file": call.get("file"),
                }
            )

    return callees


def get_dependencies(
    index: dict[str, Any],
    module_name: str,
) -> list[str]:
    """
    Get all dependencies (imports) for a module.

    Args:
        index: Index dictionary
        module_name: Name of the module

    Returns:
        List of module names that this module depends on

    Example:
        deps = get_dependencies(index, "Calculator")
        for dep in deps:
            print(f"Imports {dep}")
    """
    module = lookup_module(index, module_name)
    if not module:
        return []

    dependencies = module.get("dependencies", {})
    # Handle both old list format and new dict format for backward compatibility
    if isinstance(dependencies, list):
        # Old format: list of dicts with 'module' key
        return [dep.get("module") for dep in dependencies if "module" in dep]
    elif isinstance(dependencies, dict):
        # New format: dict with 'modules' key
        return dependencies.get("modules", [])
    else:
        return []


def get_references_to(
    index: dict[str, Any],
    module_name: str,
    function_name: str,
) -> list[dict[str, Any]]:
    """
    Get all references to a symbol (function/class).

    This includes call sites, imports, and any other references.

    Args:
        index: Index dictionary
        module_name: Name of the module containing the symbol
        function_name: Name of the symbol

    Returns:
        List of reference dictionaries with location info

    Example:
        refs = get_references_to(index, "Calculator", "add")
        print(f"Found {len(refs)} references")
    """
    # For now, references are the same as call sites
    # In future, this could include type references, imports, etc.
    call_sites = get_call_sites(index, module_name, function_name)

    # Also check if this function is called from other modules
    all_callers = get_callers_of(index, function_name)

    # Combine and deduplicate
    references = call_sites + all_callers

    return references
