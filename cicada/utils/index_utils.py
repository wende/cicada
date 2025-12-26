"""
Index file loading and saving utilities.

This module provides centralized functions for loading and saving
JSON index files with consistent error handling.
"""

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from cicada.parsing.schema import UniversalIndexSchema


def load_index(
    index_path: str | Path,
    verbose: bool = False,
    raise_on_error: bool = False,
    index_name: str | None = None,
) -> dict[str, Any] | None:
    """
    Load a JSON index file.

    Args:
        index_path: Path to the index file
        verbose: If True, print warning messages
        raise_on_error: If True, raise exceptions instead of returning None
        index_name: Optional human-readable name for the index (e.g., "PR index")

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
            name = index_name or "Index"
            print(f"Warning: {name} not found", file=sys.stderr)
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
    Save an index dictionary to a JSON file atomically.

    Uses a temp file + atomic rename pattern to prevent corruption
    during concurrent reads/writes. This is critical for background
    refresh operations where the MCP server may be reading while
    the indexer is writing.

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

    # Write to temp file first, then atomic rename
    fd, temp_path = tempfile.mkstemp(
        dir=output_file.parent,
        prefix=".index_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(index, f, indent=indent)

        # Atomic rename (works on POSIX, best-effort on Windows)
        os.replace(temp_path, output_file)

        if verbose:
            print(f"Index saved to: {output_path}")
    except Exception:
        # Clean up temp file on failure
        with contextlib.suppress(OSError):
            os.unlink(temp_path)
        raise


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
                # Check normalized visibility field (set by language indexers)
                visibility = func.get("visibility")
                if visibility == "public":
                    stats["public_functions"] += 1
                elif visibility == "private":
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
# Index Lookup and Reference Utilities
# ============================================================================
# These have been moved to separate modules for better organization.
# Re-exported here for backward compatibility.

from cicada.utils.index_lookup import (  # noqa: E402
    get_function_documentation,
    get_function_signature,
    lookup_by_location,
    lookup_function,
    lookup_module,
)
from cicada.utils.index_references import (  # noqa: E402
    get_call_sites,
    get_callees_of,
    get_callers_of,
    get_dependencies,
    get_references_to,
)

__all__ = [
    # I/O and validation
    "load_index",
    "save_index",
    "validate_index_structure",
    # Merging
    "merge_indexes",
    "merge_indexes_incremental",
    "get_index_stats",
    # Lookups (re-exported from index_lookup.py)
    "lookup_module",
    "lookup_function",
    "lookup_by_location",
    "get_function_documentation",
    "get_function_signature",
    # References (re-exported from index_references.py)
    "get_call_sites",
    "get_callers_of",
    "get_callees_of",
    "get_dependencies",
    "get_references_to",
]
