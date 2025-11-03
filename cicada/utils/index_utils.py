"""
Index file loading and saving utilities.

This module provides centralized functions for loading and saving
JSON index files with consistent error handling.
"""

import json
import sys
from pathlib import Path
from typing import Any

from cicada.parsing.schema import UniversalIndexSchema


def load_index(
    index_path: str | Path,
    verbose: bool = False,
    raise_on_error: bool = False,
) -> dict[str, Any] | None:
    """
    Load a JSON index file.

    Args:
        index_path: Path to the index file
        verbose: If True, print warning messages
        raise_on_error: If True, raise exceptions instead of returning None

    Returns:
        Index dictionary, or None if file doesn't exist or can't be loaded

    Raises:
        FileNotFoundError: If raise_on_error=True and file doesn't exist
        json.JSONDecodeError: If raise_on_error=True and JSON is invalid
        IOError: If raise_on_error=True and file can't be read
    """
    index_file = Path(index_path)

    if not index_file.exists():
        if raise_on_error:
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if verbose:
            print(f"Warning: Index not found at {index_path}", file=sys.stderr)
        return None

    try:
        with open(index_file) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        if raise_on_error:
            raise
        if verbose:
            print(f"Warning: Could not parse index: {e}", file=sys.stderr)
        return None
    except OSError as e:
        if raise_on_error:
            raise
        if verbose:
            print(f"Warning: Could not read index: {e}", file=sys.stderr)
        return None


def save_index(
    index: dict[str, Any],
    output_path: str | Path,
    indent: int = 2,
    create_dirs: bool = True,
    verbose: bool = False,
) -> None:
    """
    Save an index dictionary to a JSON file.

    Args:
        index: Index dictionary to save
        output_path: Path where the index will be saved
        indent: JSON indentation (default: 2 spaces)
        create_dirs: Create parent directories if they don't exist
        verbose: If True, print confirmation message

    Raises:
        IOError: If file cannot be written
        json.JSONEncodeError: If index cannot be serialized to JSON
    """
    output_file = Path(output_path)

    if create_dirs:
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(index, f, indent=indent)

    if verbose:
        print(f"Index saved to: {output_path}")


def validate_index_structure(
    index: Any,
    required_keys: list[str] | None = None,
    strict: bool = True,
) -> tuple[bool, str | None]:
    """
    Validate the structure of an index dictionary using UniversalIndexSchema.

    Args:
        index: Index dictionary to validate
        required_keys: List of required top-level keys (default: ['modules', 'metadata'])
                      If provided, performs basic key checking only for backward compatibility.
        strict: If True, validate all field types and constraints (default).
               If False, only validate required fields exist.

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if index is valid

    Example:
        valid, error = validate_index_structure(index)
        if not valid:
            print(f"Invalid index: {error}")
    """
    # Basic type check
    if not isinstance(index, dict):
        return False, "Index must be a dictionary"

    # Legacy mode: simple key checking for backward compatibility
    if required_keys is not None:
        for key in required_keys:
            if key not in index:
                return False, f"Missing required key: {key}"

        # Basic structure checks
        if "modules" in index and not isinstance(index["modules"], dict):
            return False, "'modules' must be a dictionary"

        if "metadata" in index and not isinstance(index["metadata"], dict):
            return False, "'metadata' must be a dictionary"

        return True, None

    # Default mode: comprehensive schema validation
    # First do basic structure check before attempting schema validation
    if "modules" not in index:
        return False, "Missing required key: modules"

    if "metadata" not in index:
        return False, "Missing required key: metadata"

    if not isinstance(index["modules"], dict):
        return False, "'modules' must be a dictionary"

    if not isinstance(index["metadata"], dict):
        return False, "'metadata' must be a dictionary"

    try:
        schema = UniversalIndexSchema.from_dict(index)
        is_valid, errors = schema.validate(strict=strict)

        if not is_valid:
            # Return first error for single-error API
            return False, errors[0] if errors else "Validation failed"

        return True, None

    except Exception as e:
        return False, f"Failed to validate index: {str(e)}"


def merge_indexes(
    *indexes: dict[str, Any],
    strategy: str = "last_wins",
) -> dict[str, Any]:
    """
    Merge multiple index dictionaries.

    Args:
        *indexes: Variable number of index dictionaries to merge
        strategy: Merge strategy ('last_wins' or 'first_wins')
            - 'last_wins': Later indexes override earlier ones
            - 'first_wins': Earlier indexes take precedence

    Returns:
        Merged index dictionary

    Example:
        merged = merge_indexes(index1, index2, index3, strategy='last_wins')
    """
    if not indexes:
        return {}

    # Start with empty structure
    merged = {
        "modules": {},
        "metadata": {},
    }

    if strategy == "last_wins":
        index_list = list(indexes)
    elif strategy == "first_wins":
        index_list = list(reversed(indexes))
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")

    # Merge modules
    for index in index_list:
        if "modules" in index:
            merged["modules"].update(index["modules"])

    # Merge metadata (later ones override)
    for index in index_list:
        if "metadata" in index:
            merged["metadata"].update(index["metadata"])

    return merged


def get_index_stats(index: dict[str, Any]) -> dict[str, Any]:
    """
    Get statistics about an index.

    Args:
        index: Index dictionary

    Returns:
        Dictionary with statistics:
        - total_modules: Number of modules
        - total_functions: Total function count
        - public_functions: Public function count
        - private_functions: Private function count

    Example:
        stats = get_index_stats(index)
        print(f"Index contains {stats['total_modules']} modules")
    """
    stats = {
        "total_modules": 0,
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
    }

    if "modules" not in index:
        return stats

    modules = index["modules"]
    stats["total_modules"] = len(modules)

    for module_data in modules.values():
        if "functions" in module_data:
            functions = module_data["functions"]
            stats["total_functions"] += len(functions)

            for func in functions:
                if func.get("type") == "def":
                    stats["public_functions"] += 1
                elif func.get("type") == "defp":
                    stats["private_functions"] += 1

    return stats


def merge_indexes_incremental(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    deleted_files: list[str],
) -> dict[str, Any]:
    """
    Merge old and new indexes for incremental reindexing.

    This specialized merge function:
    1. Keeps all modules from old_index that aren't in deleted files
    2. Adds/updates modules from new_index (new and modified files)
    3. Removes modules whose files were deleted
    4. Updates metadata with new counts and timestamp

    Args:
        old_index: Existing index dictionary
        new_index: Index from newly processed files
        deleted_files: List of file paths that were deleted

    Returns:
        Merged index dictionary with updated modules and metadata

    Example:
        merged = merge_indexes_incremental(
            old_index=existing_index,
            new_index=changed_files_index,
            deleted_files=['lib/deleted.ex']
        )
    """
    # Start with empty structure
    merged = {
        "modules": {},
        "metadata": {},
    }

    # Convert deleted files list to set for O(1) lookup
    deleted_set = set(deleted_files)

    # Keep modules from old_index that aren't deleted
    if "modules" in old_index:
        for module_name, module_data in old_index["modules"].items():
            file_path = module_data.get("file", "")
            if file_path not in deleted_set:
                merged["modules"][module_name] = module_data

    # Add/update modules from new_index (overrides old ones with same name)
    if "modules" in new_index:
        merged["modules"].update(new_index["modules"])

    # Preserve original cicada_version from old_index if it exists
    original_version = None
    if "metadata" in old_index:
        original_version = old_index["metadata"].get("cicada_version")

    # Merge metadata - take from new_index if available, else old_index
    if "metadata" in new_index:
        merged["metadata"].update(new_index["metadata"])
    elif "metadata" in old_index:
        merged["metadata"].update(old_index["metadata"])

    # Restore original version if it existed (don't overwrite with new version)
    if original_version:
        merged["metadata"]["cicada_version"] = original_version

    # Update module and function counts
    stats = get_index_stats(merged)
    merged["metadata"]["total_modules"] = stats["total_modules"]
    merged["metadata"]["total_functions"] = stats["total_functions"]
    merged["metadata"]["public_functions"] = stats["public_functions"]
    merged["metadata"]["private_functions"] = stats["private_functions"]

    return merged


# ============================================================================
# Index Lookup Utilities
# ============================================================================


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


# ============================================================================
# Reference and Call Site Utilities
# ============================================================================


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
            return func.get("calls", [])

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
            calls = func.get("calls", [])

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
) -> list[dict[str, Any]]:
    """
    Get all dependencies (imports) for a module.

    Args:
        index: Index dictionary
        module_name: Name of the module

    Returns:
        List of dependency dictionaries

    Example:
        deps = get_dependencies(index, "Calculator")
        for dep in deps:
            print(f"Imports {dep['module']}")
    """
    module = lookup_module(index, module_name)
    if not module:
        return []

    return module.get("dependencies", [])


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
