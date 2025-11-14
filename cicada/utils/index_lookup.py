"""
Index lookup utilities for finding modules, functions, and symbols.

Provides fast lookup and reverse lookup operations on Cicada indexes.
"""

from typing import Any


def lookup_module(index: dict[str, Any], module_name: str) -> dict[str, Any] | None:
    """
    Look up a module by name in the index.

    Args:
        index: Index dictionary
        module_name: Name of the module to find

    Returns:
        Module dictionary if found, None otherwise

    Example:
        module = lookup_module(index, "Calculator")
        if module:
            print(f"Found at {module['file']}:{module['line']}")
    """
    if "modules" not in index:
        return None

    return index["modules"].get(module_name)


def lookup_function(
    index: dict[str, Any],
    function_name: str,
) -> list[dict[str, Any]]:
    """
    Look up all functions with given name across all modules.

    Args:
        index: Index dictionary
        function_name: Name of the function to find

    Returns:
        List of function dictionaries with module context.
        Each dict includes the function data plus 'module_name' field.

    Example:
        matches = lookup_function(index, "add")
        for func in matches:
            print(f"{func['module_name']}.{func['name']} at line {func['line']}")
    """
    results = []

    if "modules" not in index:
        return results

    for module_name, module_data in index["modules"].items():
        if "functions" not in module_data:
            continue

        for func in module_data["functions"]:
            if func.get("name") == function_name:
                # Add module context
                func_with_context = dict(func)
                func_with_context["module_name"] = module_name
                func_with_context["file"] = module_data.get("file")
                results.append(func_with_context)

    return results


def lookup_by_location(
    index: dict[str, Any],
    file_path: str,
    line_number: int,
) -> dict[str, Any] | None:
    """
    Reverse lookup: find what's defined at a specific file/line.

    Args:
        index: Index dictionary
        file_path: File path (can be relative or just filename)
        line_number: Line number to search for

    Returns:
        Dict with 'type' (module/class/function) and 'name', or None

    Example:
        result = lookup_by_location(index, "calculator.py", 7)
        if result:
            print(f"Found {result['type']}: {result['name']}")
    """
    if "modules" not in index:
        return None

    # Normalize file path for comparison
    file_path_normalized = str(file_path).replace("\\", "/")

    # Check modules first
    for module_name, module_data in index["modules"].items():
        module_file = module_data.get("file", "").replace("\\", "/")

        # Match by filename or full path
        if file_path_normalized in module_file or module_file.endswith(file_path_normalized):
            # Check if module definition is at this line
            if module_data.get("line") == line_number:
                return {
                    "type": "class" if not module_name.startswith("_file_") else "module",
                    "name": module_name,
                    "data": module_data,
                }

            # Check functions within module
            for func in module_data.get("functions", []):
                if func.get("line") == line_number:
                    return {
                        "type": "function",
                        "name": func["name"],
                        "module": module_name,
                        "data": func,
                    }

    return None


def get_function_documentation(
    index: dict[str, Any],
    module_name: str,
    function_name: str,
) -> str | None:
    """
    Get documentation for a specific function.

    Args:
        index: Index dictionary
        module_name: Name of the module containing the function
        function_name: Name of the function

    Returns:
        Documentation string, or None if not found

    Example:
        doc = get_function_documentation(index, "Calculator", "add")
        if doc:
            print(doc)
    """
    module = lookup_module(index, module_name)
    if not module:
        return None

    for func in module.get("functions", []):
        if func.get("name") == function_name:
            return func.get("doc")

    return None


def get_function_signature(
    index: dict[str, Any],
    module_name: str,
    function_name: str,
) -> str | None:
    """
    Get signature for a specific function.

    Args:
        index: Index dictionary
        module_name: Name of the module containing the function
        function_name: Name of the function

    Returns:
        Signature string, or None if not found

    Example:
        sig = get_function_signature(index, "Calculator", "add")
        # Returns: "def add(self, x: int, y: int) -> int:"
    """
    module = lookup_module(index, module_name)
    if not module:
        return None

    for func in module.get("functions", []):
        if func.get("name") == function_name:
            return func.get("signature")

    return None
